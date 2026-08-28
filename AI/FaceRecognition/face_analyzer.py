"""
Face Analyzer Module — Parallel & Cached Edition
EXIF-aware face detection, agglomerative clustering, photo categorization
and multiprocess scanning.
"""

import os
import concurrent.futures
import multiprocessing
from typing import List, Dict, Tuple, Optional, Callable, Union, Set

import face_recognition
import numpy as np
from PIL import Image, ImageOps

from face_cache import CacheManager, generate_grid_thumbnail

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}

# Thresholds expressed as euclidean distance between 128-d face encodings.
# Distances between a face and a group are k-nearest-neighbour distances: the
# 0.6 threshold of face_recognition is calibrated on pairs of faces, so the
# average over every member of a cluster (poses, light, age) rejects true
# matches, while the plain minimum lets clusters chain into each other.
DEFAULT_TOLERANCE = 0.6      # face -> cluster assignment
MERGE_TOLERANCE = 0.58       # merge two clusters of the same person
MATCH_TOLERANCE = 0.55       # strong evidence that a face assigned elsewhere is still this person
KNN_NEIGHBORS = 3            # neighbours averaged to compare a face with a cluster
MAX_CLUSTER_SAMPLE = 40      # members sampled per cluster when computing linkage distances
MAX_ANALYSIS_DIM = 2000      # images are downscaled before detection (speed + stable encodings)
REFINE_PASSES = 2            # merge/reassign iterations after the first greedy pass
MIN_PARALLEL_BATCH = 8       # below this, starting worker processes costs more than it saves


def scan_folder(folder_path: str, recursive: bool = False) -> List[str]:
    """
    Scan a folder for supported image files.
    With recursive=True every subfolder is walked too (hidden ones excluded).
    """
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        return []

    def images_in(directory: str, filenames) -> List[str]:
        found = []
        for filename in sorted(filenames):
            if os.path.splitext(filename)[1].lower() in SUPPORTED_EXTENSIONS:
                full_path = os.path.join(directory, filename)
                if os.path.isfile(full_path):
                    found.append(full_path)
        return found

    if not recursive:
        try:
            return images_in(folder_path, os.listdir(folder_path))
        except OSError:
            return []

    images: List[str] = []
    for root, subdirs, filenames in os.walk(folder_path):
        subdirs[:] = sorted(d for d in subdirs if not d.startswith('.'))
        images.extend(images_in(root, filenames))
    return images


# ── Detection ────────────────────────────────────────────────────────

def load_image_for_analysis(image_path: str,
                            max_dimension: int = MAX_ANALYSIS_DIM) -> Tuple[np.ndarray, float]:
    """
    Load an image as RGB honouring the EXIF orientation flag.
    face_recognition.load_image_file() ignores EXIF, so rotated photos from
    phones/cameras were analyzed sideways and their faces were never detected.
    Returns (rgb_array, scale) where scale is the applied downscale factor.
    """
    with Image.open(image_path) as orig:
        image = ImageOps.exif_transpose(orig).convert('RGB')
        scale = 1.0
        longest = max(image.size)
        if max_dimension and longest > max_dimension:
            scale = max_dimension / float(longest)
            image = image.resize(
                (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
                Image.LANCZOS
            )
        return np.array(image), scale


def _rescale_location(location: tuple, factor: float) -> tuple:
    """Map a face box back to full resolution coordinates."""
    top, right, bottom, left = location
    return (int(round(top * factor)), int(round(right * factor)),
            int(round(bottom * factor)), int(round(left * factor)))


def detect_faces(image_path: str) -> Tuple[List[np.ndarray], List[tuple]]:
    """
    Detect faces in a single image (no cache).
    Locations are returned in full resolution / EXIF-corrected coordinates,
    the same reference frame used by extract_face_thumbnail().
    """
    image, scale = load_image_for_analysis(image_path)

    locations = face_recognition.face_locations(image, number_of_times_to_upsample=1, model='hog')
    if not locations:
        # Second chance for small or distant faces (group shots, landscapes).
        locations = face_recognition.face_locations(image, number_of_times_to_upsample=2, model='hog')

    encodings = list(face_recognition.face_encodings(image, locations))
    factor = 1.0 / scale if scale else 1.0
    return encodings, [_rescale_location(loc, factor) for loc in locations]


def analyze_single_image(image_path: str,
                         cache_mgr: Optional[CacheManager] = None) -> Tuple[List[np.ndarray], List[tuple]]:
    """
    Analyze a single image for faces, using the SQLite cache when available.
    Returns (encodings, locations).
    """
    if cache_mgr:
        cached = cache_mgr.get_cached_image(image_path)
        if cached is not None:
            encodings, locations, _ = cached
            return encodings, locations

    try:
        enc_list, loc_list = detect_faces(image_path)
        if cache_mgr:
            thumb_blob = generate_grid_thumbnail(image_path)
            cache_mgr.save_cached_image(image_path, enc_list, loc_list, thumb_blob)
        return enc_list, loc_list
    except Exception as e:
        print(f"[WARN] Error analyzing {os.path.basename(image_path)}: {e}")
        return [], []


def _analyze_worker(image_path: str):
    """Subprocess entry point: detection + thumbnail, no DB access."""
    try:
        encodings, locations = detect_faces(image_path)
        return image_path, encodings, locations, generate_grid_thumbnail(image_path), None
    except Exception as e:
        return image_path, [], [], None, str(e)


def analyze_folder_parallel(
    image_paths: List[str],
    cache_mgr: CacheManager,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    max_workers: int = 0
) -> Dict[str, Tuple[List[np.ndarray], List[tuple]]]:
    """
    Analyze a list of images with SQLite caching.
    Uncached files are detected in separate processes (dlib is not thread safe,
    but it is process safe); the cache is written only from the parent process.
    max_workers=0 means auto.
    """
    results: Dict[str, Tuple[List[np.ndarray], List[tuple]]] = {}
    total = len(image_paths)
    pending: List[str] = []

    def report(path: str):
        if progress_callback:
            progress_callback(len(results), total, os.path.basename(path))

    for path in image_paths:
        cached = cache_mgr.get_cached_image(path) if cache_mgr else None
        if cached is not None:
            results[path] = (cached[0], cached[1])
            report(path)
        else:
            pending.append(path)

    workers = max_workers or min(4, os.cpu_count() or 1)
    workers = max(1, min(workers, os.cpu_count() or 1))

    if len(pending) >= MIN_PARALLEL_BATCH and workers > 1:
        try:
            ctx = multiprocessing.get_context("spawn")
            with concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
                for path, enc, loc, thumb, err in pool.map(_analyze_worker, pending):
                    if err:
                        print(f"[WARN] Error analyzing {os.path.basename(path)}: {err}")
                    else:
                        if cache_mgr:
                            cache_mgr.save_cached_image(path, enc, loc, thumb)
                    results[path] = (enc, loc)
                    report(path)
        except Exception as e:
            print(f"[WARN] Parallel scan unavailable ({e}); falling back to sequential")

    for path in pending:
        if path in results:
            continue
        results[path] = analyze_single_image(path, cache_mgr)
        report(path)

    return results


def extract_face_thumbnail(image_path: str, location: tuple,
                           size: int = 120) -> Optional[Image.Image]:
    """Extract face thumbnail with padding around face."""
    try:
        with Image.open(image_path) as orig_img:
            image = ImageOps.exif_transpose(orig_img).convert('RGB')
            top, right, bottom, left = location
            h, w = bottom - top, right - left
            pad = int(max(h, w) * 0.4)
            top = max(0, top - pad)
            left = max(0, left - pad)
            bottom = min(image.height, bottom + pad)
            right = min(image.width, right + pad)
            face_img = image.crop((left, top, right, bottom))
            face_img = face_img.resize((size, size), Image.LANCZOS)
            return face_img
    except Exception:
        return None


# ── Clustering ───────────────────────────────────────────────────────

def _distance_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Euclidean distances between every row of a and every row of b."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    sq = (a * a).sum(axis=1)[:, None] + (b * b).sum(axis=1)[None, :] - 2.0 * (a @ b.T)
    return np.sqrt(np.maximum(sq, 0.0))


def _knn_distance(distances: np.ndarray, axis: int = -1, k: int = KNN_NEIGHBORS) -> np.ndarray:
    """Mean of the k smallest distances along an axis (k-nearest-neighbour linkage)."""
    kk = max(1, min(k, distances.shape[axis]))
    nearest = np.sort(distances, axis=axis)
    slicer: List = [slice(None)] * distances.ndim
    slicer[axis] = slice(0, kk)
    return nearest[tuple(slicer)].mean(axis=axis)


def _cluster_sample(cluster: Dict, max_members: int = MAX_CLUSTER_SAMPLE) -> np.ndarray:
    """Evenly spread subset of a cluster's encodings, used for linkage distances."""
    cached = cluster.get('_sample')
    if cached is not None:
        return cached
    encodings = cluster['encodings']
    if len(encodings) <= max_members:
        sample = np.asarray(encodings, dtype=np.float64)
    else:
        idx = np.linspace(0, len(encodings) - 1, max_members).astype(int)
        sample = np.asarray([encodings[i] for i in idx], dtype=np.float64)
    cluster['_sample'] = sample
    return sample


def _new_cluster(image_path: str, location: tuple, encoding: np.ndarray) -> Dict:
    return {
        'encodings': [encoding],
        'occurrences': [(image_path, location)],
        'representative': encoding.copy(),
    }


def _add_to_cluster(cluster: Dict, image_path: str, location: tuple, encoding: np.ndarray):
    cluster['encodings'].append(encoding)
    cluster['occurrences'].append((image_path, location))
    cluster['_sample'] = None


def _face_distances_to_clusters(clusters: List[Dict], encoding: np.ndarray) -> np.ndarray:
    """k-NN distance of one face to every cluster."""
    enc = np.asarray(encoding, dtype=np.float64)[None, :]
    return np.array([float(_knn_distance(_distance_matrix(enc, _cluster_sample(c))[0]))
                     for c in clusters])


def _cluster_distance(a: Dict, b: Dict) -> float:
    """Symmetric k-NN distance between two clusters."""
    distances = _distance_matrix(_cluster_sample(a), _cluster_sample(b))
    return float((_knn_distance(distances, axis=1).mean()
                  + _knn_distance(distances, axis=0).mean()) / 2.0)


def _merge_similar_clusters(clusters: List[Dict], threshold: float) -> List[Dict]:
    """
    Repeatedly merge the closest pair of clusters (k-NN linkage) while it
    stays below the threshold. Fixes the fragmentation of a single person into
    several clusters caused by pose/lighting changes.
    """
    clusters = list(clusters)
    ids = list(range(len(clusters)))
    next_id = len(clusters)
    cache: Dict[Tuple[int, int], float] = {}   # only the merged cluster is recomputed

    while len(clusters) > 1:
        best_pair, best_dist = None, threshold
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                key = (ids[i], ids[j])
                dist = cache.get(key)
                if dist is None:
                    dist = _cluster_distance(clusters[i], clusters[j])
                    cache[key] = dist
                if dist < best_dist:
                    best_dist, best_pair = dist, (i, j)

        if best_pair is None:
            break

        i, j = best_pair
        stale = {ids[i], ids[j]}
        clusters[i]['encodings'].extend(clusters[j]['encodings'])
        clusters[i]['occurrences'].extend(clusters[j]['occurrences'])
        clusters[i]['_sample'] = None
        clusters.pop(j)
        ids[i] = next_id
        next_id += 1
        ids.pop(j)
        cache = {k: v for k, v in cache.items() if not stale & set(k)}

    return clusters


def _reassign_faces(clusters: List[Dict], faces: List[Tuple[str, tuple, np.ndarray]],
                    tolerance: float) -> List[Dict]:
    """
    Re-assign every face to its closest cluster (k-NN linkage), so the final
    grouping no longer depends on the order the images were scanned in.
    """
    if not clusters:
        return clusters

    centers = [{'encodings': list(c['encodings']), 'occurrences': [], '_sample': None}
               for c in clusters]
    for c in centers:
        _cluster_sample(c)

    rebuilt: List[Dict] = [{'encodings': [], 'occurrences': [], '_sample': None} for _ in centers]
    for image_path, location, encoding in faces:
        distances = _face_distances_to_clusters(centers, encoding)
        best = int(np.argmin(distances))
        if distances[best] <= tolerance:
            rebuilt[best]['encodings'].append(encoding)
            rebuilt[best]['occurrences'].append((image_path, location))
        else:
            rebuilt.append(_new_cluster(image_path, location, encoding))

    return [c for c in rebuilt if c['occurrences']]


def cluster_faces(face_data: Dict[str, Tuple[List[np.ndarray], List[tuple]]],
                  tolerance: float = DEFAULT_TOLERANCE) -> List[Dict]:
    """
    Cluster faces across images (greedy pass + merge/reassign refinement).

    Every cluster exposes:
      - occurrences / encodings : faces assigned to the cluster
      - photo_paths             : photos owning one of those faces
      - match_paths             : photo_paths plus photos holding a face that is
                                  a strong match (MATCH_TOLERANCE) for this
                                  person although assigned to another cluster
      - photo_count             : len(match_paths) — what the UI displays and
                                  what categorize_photos() uses, so the two can
                                  never disagree
    Sorted by photo_count descending: cluster 0 is the most frequent person.
    """
    faces: List[Tuple[str, tuple, np.ndarray]] = []
    for image_path in sorted(face_data.keys()):
        encodings, locations = face_data[image_path]
        for enc, loc in zip(encodings, locations):
            faces.append((image_path, loc, np.asarray(enc, dtype=np.float64)))

    if not faces:
        return []

    clusters: List[Dict] = []
    for image_path, location, encoding in faces:
        if clusters:
            distances = _face_distances_to_clusters(clusters, encoding)
            best = int(np.argmin(distances))
            if distances[best] <= tolerance:
                _add_to_cluster(clusters[best], image_path, location, encoding)
                continue
        clusters.append(_new_cluster(image_path, location, encoding))

    for _ in range(REFINE_PASSES):
        merged = _merge_similar_clusters(clusters, MERGE_TOLERANCE)
        clusters = _reassign_faces(merged, faces, tolerance)
        if len(clusters) == len(merged):
            break   # reassignment moved nothing: the grouping is stable

    # Reassignment can leave fresh singletons behind: give them a last chance.
    clusters = _merge_similar_clusters(clusters, MERGE_TOLERANCE)

    _finalize_clusters(clusters, faces, tolerance)
    clusters.sort(key=lambda c: (c['photo_count'], len(c['encodings'])), reverse=True)
    return clusters


def _finalize_clusters(clusters: List[Dict], faces: List[Tuple[str, tuple, np.ndarray]],
                       tolerance: float):
    """Compute representative, thumbnail source and the photo sets of each cluster."""
    all_encodings = np.asarray([f[2] for f in faces], dtype=np.float64)

    for cluster in clusters:
        cluster['_sample'] = None
        representative = np.mean(np.asarray(cluster['encodings'], dtype=np.float64), axis=0)
        cluster['representative'] = representative

        # Thumbnail from the face closest to the cluster average, not the first seen.
        distances = _distance_matrix(representative[None, :],
                                     np.asarray(cluster['encodings'], dtype=np.float64))[0]
        cluster['thumbnail_source'] = cluster['occurrences'][int(np.argmin(distances))]

        photo_paths = {path for path, _ in cluster['occurrences']}

        # Faces assigned to another cluster but still a strong match for this
        # person: keeping them out of "senza persona" avoids false negatives.
        near = _knn_distance(_distance_matrix(_cluster_sample(cluster), all_encodings), axis=0)
        match_paths = set(photo_paths)
        for idx in np.nonzero(near <= min(tolerance, MATCH_TOLERANCE))[0]:
            match_paths.add(faces[int(idx)][0])

        cluster['photo_paths'] = sorted(photo_paths)
        cluster['match_paths'] = sorted(match_paths)
        cluster['photo_count'] = len(match_paths)
        cluster['face_count'] = len(cluster['encodings'])


# ── Categorization ───────────────────────────────────────────────────

def categorize_photos(
    image_paths: List[str],
    face_data: Dict[str, Tuple[List[np.ndarray], List[tuple]]],
    target: Union[Dict, np.ndarray, None],
    tolerance: float = DEFAULT_TOLERANCE,
) -> Tuple[List[str], List[str], List[str]]:
    """
    Categorize photos against a target person:
    - with_target   : contains the target face
    - without_target: has faces, none of them is the target
    - no_faces      : no face detected at all

    `target` is normally the cluster dict returned by cluster_faces(): the photo
    sets computed while clustering are reused, so "senza persona" is exactly the
    complement of the cluster shown in the sidebar. A bare encoding is still
    accepted (legacy callers) and compared face by face.
    """
    with_target, without_target, no_faces = [], [], []

    matched: Optional[Set[str]] = None
    reference: Optional[np.ndarray] = None

    if isinstance(target, dict):
        matched = set(target.get('match_paths') or target.get('photo_paths') or
                      [p for p, _ in target.get('occurrences', [])])
    elif target is not None:
        reference = np.asarray(target, dtype=np.float64)[None, :]

    for path in image_paths:
        encodings, _ = face_data.get(path, ([], []))
        if not encodings:
            no_faces.append(path)
            continue

        if matched is not None:
            found = path in matched
        elif reference is not None:
            distances = _distance_matrix(reference,
                                         np.asarray(encodings, dtype=np.float64))[0]
            found = bool((distances <= tolerance).any())
        else:
            found = False  # no target selected: nothing can match

        (with_target if found else without_target).append(path)

    return with_target, without_target, no_faces
