#see https://docs.python.org/3/library/difflib.html

#This module provides classes and functions for comparing sequences. 
#It can be used for example, for comparing files, and can produce information about file
#  differences in various formats, including HTML and context and unified diffs. 
#For comparing directories and files, see also, the filecmp module.
import difflib  as difflib 
from pprint import pprint

#difflib.context_diff(a, b, fromfile='', tofile='', fromfiledate='', tofiledate='', n=3, lineterm='\n')¶
#Compare a and b (lists of strings); return a delta (a generator generating the delta lines) in context diff format.
print ("---- context_diff : ---- ")
s1 = ['bacon\n', 'eggs\n', 'ham\n', 'guido\n']
s2 = ['python\n', 'eggy\n', 'hamster\n', 'guido\n']
d=difflib.context_diff(s1, s2)
delta = '-'.join(d)
print(delta)


print(" ----- get_close_matches ----- ")
#Return a list of the best “good enough” matches. word is a sequence for which close matches are desired (typically a string), and possibilities is a list of sequences against which to match word (typically a list of strings).
l=difflib.get_close_matches('appel', ['ape', 'apple', 'peach', 'puppy'])
print(l)



print(" ----- ndiff -----")
#Compare a and b (lists of strings); return a Differ-style delta (a generator generating the delta lines).
diff = difflib.ndiff(
    'one\ntwo\nthree\n'.splitlines(keepends=True),
    'one\ntree\nemu\n'.splitlines(keepends=True))
print(''.join(diff), end="")

print(" ----- restore -----")
#Return one of the two sequences that generated a delta.
diff = difflib.ndiff(
    'one\ntwo\nthree\n'.splitlines(keepends=True),
    'one\ntree\nemu\n'.splitlines(keepends=True))
diff = list(diff) # materialize the generated delta into a list
print(''.join(difflib.restore(diff, 1)), end="")

print(" ----- unified_diff -----")
#Compare a and b (lists of strings); return a delta (a generator generating the delta lines) in unified diff format.
s1 = ['bacon\n', 'eggy\n', 'ham\n', 'guido\n']
s2 = ['python\n', 'eggy\n', 'hamster\n', 'guido\n']
diff=difflib.unified_diff(s1, s2, fromfile='before.py', tofile='after.py')
print(''.join(diff), end="")

print(" ----- SequenceMatcher -----")
#The SequenceMatcher class has this constructor:
s = difflib.SequenceMatcher(lambda x: x == " ",
                    "private Thread currentThread;",
                    "private volatile Thread currentThread;")

print(" ----- find_longest_match -----")
#Find longest matching block in a[alo:ahi] and b[blo:bhi].
s = difflib.SequenceMatcher(None, " abcd", "abcd abcd")
diff = s.find_longest_match(0, 5, 0, 9)
print(diff)


print(" ----- ratio -----")
#Return a measure of the sequences’ similarity as a float in the range [0, 1].
s=difflib.SequenceMatcher(None, 'tide', 'diet').ratio()
print(s)
s=difflib.SequenceMatcher(None, 'diet', 'tide').ratio()
print(s)
 

print(" ----- Differ -----")
#The Differ class has this constructor:
#Note that Differ-generated deltas make no claim to be minimal diffs.
text1 = '''  1. Beautiful is better than ugly.
  2. Explicit is better than implicit.
  3. Simple is better than complex.
  4. Complex is better than complicated.
'''.splitlines(keepends=True)
text2 = '''  1. Beautiful is better than ugly.
  3.   Simple is better than complex.
  4. Complicated is better than complex.
  5. Flat is better than nested.
'''.splitlines(keepends=True)
d = difflib.Differ()
result = list(d.compare(text1, text2))
pprint(result)

print(" ----- ratio -----")
print(" ----- ratio -----")
print(" ----- ratio -----")
print(" ----- ratio -----")
print(" ----- ratio -----")