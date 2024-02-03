//see https://www.youtube.com/watch?v=w-rti-5KHME

var map = L.map('map').setView([51.505, -0.09], 13);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

let selectedPlace=undefined;
let submitButton=document.getElementById("btnSubmit");
let lat=document.getElementById("lat");
let lng=document.getElementById("lng");
submitButton.setAttribute("disabled","disabled");
function onMapClick(e) {
    console.log("You clicked the map at " + e.latlng);
    selectedPlace=e.latlng
    submitButton.removeAttribute("disabled");
    lat.value=selectedPlace.lat;
    lng.value=selectedPlace.lng;
}
map.on('click', onMapClick);

//var marker = L.marker([51.5, -0.09]).addTo(map);
fetch('/api/notes')
    .then(response => response.json())
    .then(data => {
        data.map(el => {
            const marker = L.marker([el.lat, el.lng]).addTo(map);
            marker.bindPopup(el.content);//.openPopup();
        })
    } );