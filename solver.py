#!/usr/bin/env python
#
# WWF/scrabble solver based on
#  http://www.cs.cmu.edu/afs/cs/academic/class/15451-s06/www/lectures/scrabble.pdf
#  http://ericsink.com/downloads/faster-scrabble-gordon.pdf
#
# python2; see board, words for file formats
#

import sys
import string
import copy
import argparse

class Node(object):
    counter = 0

    def __str__(self):
	return "N" + str(self.number)

    def __init__(self):
	Node.counter += 1
	self.number = Node.counter
	self.edges = {}

    def dump(self, out, seen):
	if self.number in seen:
	    return
	seen.add(self.number)
	for k, v in self.edges.iteritems():
	    v.dump(out, self, seen)

    def add_arc(self, ch):
	if ch not in self.edges:
	    self.edges[ch] = Edge(ch)
	return self.edges[ch].target

    def add_final_arc(self, c1, c2):
	 n = self.add_arc(c1)
	 self.edges[c1].add_letter(c2)
	 return n

    def force_arc(self, ch, fst):
	if ch in self.edges:
	    if self.edges[ch].target != fst:
		print "force_arc error!", fst, self.edges[ch].target, ch
		sys.exit(1)
	else:
	    self.edges[ch] = Edge(ch, fst)
	return self.edges[ch]

class Edge(object):
    def __init__(self, ch, target=None):
	self.ch = ch
	self.letters = set()

	if target == None:
	    target = Node()
	self.target = target
	pass

    def str_letter_set(self):
	rv = ""
	if self.letters and (len(self.letters) > 0):
	    rv = " ["
	    for k in self.letters:
		rv += k
	    rv += "]"
	return rv

    def dump(self, out, source, seen):
	mn = self.ch + self.str_letter_set()
	print >> out, source, "->", self.target, "[label=\"" + mn + '"];'
	self.target.dump(out, seen)

    def add_letter(self, ch):
	self.letters.add(ch)

    def has_letter(self, ch):
	return ch in self.letters

    def next_arc(self, ch):
	if ch in self.target.edges:
	    return self.target.edges[ch]
	return None

class GADDAG(object):
    def __init__(self, wordfile):
	self.count = 0
	self.initialState = Node()
	self.initialArc = Edge('$', self.initialState)
	self.load(wordfile)
	self.all_letters = set()
	for i in string.lowercase:
		self.all_letters.add(i)

    def load(self, wordfile):
	with open(wordfile, 'r') as inp:
	    for line in inp.readlines():
		if line[0].isupper(): # likely proper name, not accepted
		    continue
		self.add_word(line.rstrip().lower())
	print "loaded", self.count, "words"

    def add_word(self, word):
	if len(word) < 2:
	    return

	self.count += 1
	if (self.count % 5000) == 0:
	    print "...", self.count, word

	st = self.initialState
	for i in reversed(range(2, len(word))):
	    st = st.add_arc(word[i])
	st.add_final_arc(word[1], word[0])

	st = self.initialState
	for i in reversed(range(0, len(word) - 1)):
	    st = st.add_arc(word[i])
	st = st.add_final_arc('$', word[-1])

	final_state = st
	for m in reversed(range(1, len(word) - 2 + 1)):
	    force = st
	    st = self.initialState
	    for i in reversed(range(1, m + 1)):
		st = st.add_arc(word[i-1])
	    st = st.add_arc('$')

	    narc = st.force_arc(word[m+1-1], force)
	    if force == final_state:
		narc.add_letter(word[-1])

    def dump(self, fname):
	with open(fname, 'w') as out:
	    seen = set()
	    print >> out,  "digraph {"
	    self.initialState.dump(out, seen)
	    print >> out, "}"

    def lookup_path(self, arc, path):
	for p in path:
	    arc = arc.next_arc(p)
	    if arc == None:
		return None
	return arc

    def is_word(self, word):
	path = word[0] + "$" + word[1:-1]
	arc = self.lookup_path(self.initialArc, path)
	if arc:
	    return arc.has_letter(word[-1])
	return False

    def cross_set_prefix(self, word):
	prefix = set()
	for i in string.lowercase:
	    path = i + "$" + word[:-1]
	    arc = self.lookup_path(self.initialArc, path)
	    if arc and arc.has_letter(word[-1]):
		prefix.add(i)
	return prefix

    def cross_set_suffix(self, word):
	path = word[0] + "$" + word[1:]
	arc = self.lookup_path(self.initialArc, path)
	if arc and arc.letters:
	    return arc.letters
	return set()

    def cross_set_middle(self, prefix, suffix):
	middle = set()
	path = prefix[::-1] + "$"
	arc = self.lookup_path(self.initialArc, path)
	if arc == None:
	    return set()
	for i in string.lowercase:
	    rest = i + suffix[:-1]
	    rarc = self.lookup_path(arc, rest)
	    if rarc and rarc.has_letter(suffix[-1]):
		middle.add(i)
	return middle

    def cross_set(self, left, right):
	if len(left) and len(right):
	    return self.cross_set_middle(left, right)
	elif len(right):
	    return self.cross_set_prefix(right)
	elif len(left):
	    return self.cross_set_suffix(left)
	else:
	    return self.all_letters

class Board(object):
    multipliers = [ '---t--T-T--t---',
		    '--D--d---d--D--',
		    '-D--D-----D--D-',
		    't--T---d---T--t',
		    '--D---D-D---D--',
		    '-d---T---T---d-',
		    'T---D-----D---T',
		    '---d-------d---',
		    'T---D-----D---T',
		    '-d---T---T---d-',
		    '--D---D-D---D--',
		    't--T---d---T--t',
		    '-D--D-----D--D-',
		    '--D--d---d--D--',
		    '---t--T-T--t---' ]

    def add_points(self, pt, s):
	for i in s:
	    self.letter_points[i] = pt

    def __init__(self, fname):
	self.rack = set()
	self.board = []
	self.load(fname)
	self.letter_points = {}

	self.add_points(0, "*")
	self.add_points(1, "srtioae")
	self.add_points(2, "ludn")
	self.add_points(3, "ygh")
	self.add_points(4, "bcfmpw")
	self.add_points(5, "kv")
	self.add_points(8, "x")
	self.add_points(10, "jqz")

    def parse_rack(self, line):
	self.rack = list(line.lower())

    def parse_push_row(self, line):
	row = list(line.lower())
	self.board.append(row)

    def load(self, fname):
	with open(fname, 'r') as inp:
	    self.parse_rack(inp.readline().strip())
	    for line in inp.readlines():
		self.parse_push_row(line.strip())

    def rows(self):
	return len(self.board)

    def cols(self):
	return len(self.board[0])

    def get_letter(self, row, col):
	L = self.board[row][col];
	if L == '-':
	    return None
	return L

    def patch(self, a, word):
	for L in word:
	    if self.board[a.row][a.col] == '-':
	        self.board[a.row][a.col] = L
	    a = a.add(1)

    def pretty_print(self):
	for r in self.board:
	    s=""
	    for c in r:
		s += c
		s += " "
	    print s

    def pretty_print_word(self, a, word):
	x = copy.deepcopy(self)
	x.patch(a, word)
	x.pretty_print()

    def word_multiplier_at(self, row, col):
	m = self.multipliers[row][col]
	if m == 'd': return 2
	if m == 't': return 3
	return 1

    def letter_multiplier_at(self, row, col):
	m = self.multipliers[row][col]
	if m == 'D': return 2
	if m == 'T': return 3
	return 1

class Anchor(object):
    def __init__(self, row, col, a=0):
	self.row = row
	self.col = col
	self.a = a

    def __eq__(self, other):
	if type(other) is type(self):
	    return  (self.row == other.row) and (self.col == other.col) and (self.a == other.a)
	return False

    def __ne__(self, other):
	return not self.__eq__(other)

    def direction(self):
	if self.a:
	    return "v"
	return "h"

    def add(self, pos):
	n = Anchor(self.row, self.col)
	n.a = self.a
	if self.a:
	    n.row += pos
	else:
	    n.col += pos
	return n

    def __str__(self):
	return "<Anchor r:" + str(self.row) + " c:" + str(self.col) + " a:" + str(self.a) + ">"


class Solution(object):
    def __init__(self, start, word, score, played):
	self.start = start
	self.word = word
	self.score = score
	self.played = played

    def __eq__(self, other):
	if type(other) is type(self):
	    return (self.start == other.start) and (self.word == other.word)
	return False

    def __ne__(self, other):
	return not self.__eq__(other)

    def __hash__(self):
	return str(self).__hash__()

    def __str__(self):
	s = "<PLAY: @"
	s += str(self.start.row) + "," + str(self.start.col) + " ";
	s += self.start.direction() + " "
	s += self.word + " " + str(self.score) + ">"
	return s

class Solver(object):
    def __init__(self, board, gaddag):
	self.board = board
	self.gaddag = gaddag
	self.anchor = None
	self.rows = board.rows()
	self.cols = board.cols()
	self.plays = set()

    def is_valid_address(self, row, col):
	if (row < 0) or (col < 0) or (row >= self.rows) or (col >= self.cols):
	    return False
	return True

    def test_anchor(self, row, col):
	if self.is_valid_address(row, col):
	    if None != board.get_letter(row, col):
		return True
	return False

    def get_anchors(self):
	anchors = []
	for row in range(0, board.rows()):
	    for col in range(0, board.cols()):
		if None == board.get_letter(row, col):
		    ok = False
		    ok |= self.test_anchor(row, col + 1)
		    ok |= self.test_anchor(row, col - 1)
		    ok |= self.test_anchor(row + 1, col)
		    ok |= self.test_anchor(row - 1, col)
		    if ok:
			anchors.append(Anchor(row, col, 0))
			anchors.append(Anchor(row, col, 1))
	return anchors

    def print_play(self, play):
	print play
	board.pretty_print_word(play.start, play.word.upper())

    def solve(self):
	anchors = self.get_anchors()
	self.plays = set()
	for self.anchor in anchors:
	    self.gen(0, "", board.rack, [0], [], gaddag.initialArc)
	for p in sorted(self.plays, key=lambda o: o.score):
	    self.print_play(p)

    def get_letter(self, a):
	return board.get_letter(a.row, a.col)

    def abs_position(self, anchor, pos):
	n = anchor.add(pos)
	if self.is_valid_address(n.row, n.col):
	    return n
	return None

    def get_square_letter(self, pos):
	return self.get_letter(self.abs_position(self.anchor, pos))

    def slurp_direction(self, start, pos, direction, s="", score=0):
	pos += direction

	n = self.abs_position(start, pos)
	if n == None:
	    return score, s
	L = self.get_letter(n)
	if L == None:
	    return score, s
	if direction > 0:
	    s += L
	else:
	    s = L + s
	score += self.get_letter_points(L)
	return self.slurp_direction(start, pos, direction, s, score)

    # anchor + pos, return partial score, cross-set
    def get_square_cross_set(self, pos):
	start = self.abs_position(self.anchor, pos)
	start.a ^= 1

	left_score, left = self.slurp_direction(start, 0, -1)
	right_score, right = self.slurp_direction(start, 0, 1)

	ss = gaddag.cross_set(left, right)

	# if len(left) or len(right):
	#    print start, "left '" + left + "' right '" + right + "' :", ss

	return (left_score + right_score), ss

    def calculate_score(self, remaining_rack, score, multipliers):
	calculated_score = 0
	my_score = score[:]
	if len(remaining_rack) == 0:
	    calculated_score += 35

	for i in sorted(multipliers, reverse=True):
	    my_score[0] *= i
	return calculated_score + sum(my_score)

    def played_tiles(self, remaining_rack):
	played = board.rack[:]
	s = ""
	for i in remaining_rack: played.remove(i)
	for i in played: s += i
	return s

    def word_start(self, pos, word):
	if pos > 0:
	    n = self.anchor.add(pos - len(word) + 1)
	else:
	    n = self.anchor.add(pos)
	return n

    # record word at anchor
    def record_play(self, pos, word, remaining_rack, score, multipliers):
	sc = self.calculate_score(remaining_rack, score, multipliers)
	ws = self.word_start(pos, word)
	pt = self.played_tiles(remaining_rack)

	play = Solution(ws, word, sc, pt)
	self.plays.add(play)

    # is there an empty square here [anchor + pos] ?
    def is_empty_at(self, pos):
	n = self.abs_position(self.anchor, pos)
	return (n and (None == self.get_letter(n)))

    # [anchor + pos] is empty/edge of board?
    def does_terminate(self, pos):
	n = self.abs_position(self.anchor, pos)
	return (not n or (None == self.get_letter(n)))

    # [anchor + pos] valid board position?
    def can_i_go(self, pos):
	return self.abs_position(self.anchor, pos)

    # points for given letter
    def get_letter_points(self, L):
	return self.board.letter_points[L]

    def get_letter_multiplier(self, pos):
	n = self.abs_position(self.anchor, pos)
	return self.board.letter_multiplier_at(n.row, n.col)

    def get_word_multiplier(self, pos):
	n = self.abs_position(self.anchor, pos)
	return self.board.word_multiplier_at(n.row, n.col)

    def gen(self, pos, word, rack, score, multipliers, arc):
	# print "GE", self.anchor, pos, word, rack, score
	L = self.get_square_letter(pos)
	if L != None:
	    score[0] += self.get_letter_points(L)
	    self.goon(pos, L, word, rack, score, multipliers, arc.next_arc(L), arc)
	elif len(rack):
	    partial, cross_set = self.get_square_cross_set(pos)
	    tried_set = set()

	    for index in range(0, len(rack)):
		new_rack = rack[:]
		L = new_rack[index]
		del new_rack[index]

		new_score = score[:]
		new_multipliers = multipliers[:]

		letter_score = self.get_letter_points(L) * self.get_letter_multiplier(pos)
		mult = self.get_word_multiplier(pos)

		new_score[0] += letter_score
		new_multipliers.append(mult)
		if partial > 0:
		    new_score.append(mult * (partial + letter_score))

		if L == '*':
		    for L in (cross_set.difference(tried_set)):
			self.goon(pos, L, word, new_rack, new_score, new_multipliers, arc.next_arc(L), arc)
			tried_set.add(L)
		elif L in cross_set and L not in tried_set:
		    self.goon(pos, L, word, new_rack, new_score, new_multipliers, arc.next_arc(L), arc)
		    tried_set.add(L)


    def goon(self, pos, L, word, rack, score, multipliers, new_arc, old_arc):
	# print "GO", pos, L, word, rack, new_arc, old_arc, score
	if pos <= 0:
	    word = L + word
	    if old_arc.has_letter(L) and self.does_terminate(pos - 1) and self.is_empty_at(1):
		self.record_play(pos, word, rack, score, multipliers)
	    if new_arc:
		if self.can_i_go(pos - 1):
		    self.gen(pos - 1, word, rack, score, multipliers, new_arc)
		new_arc = new_arc.next_arc('$')
		if new_arc and self.does_terminate(pos - 1) and self.can_i_go(1):
		    self.gen(1, word, rack, score, multipliers, new_arc)
	else:
	    word = word + L
	    if old_arc.has_letter(L) and self.does_terminate(pos + 1):
		self.record_play(pos, word, rack, score, multipliers)
	    if new_arc and self.can_i_go(pos + 1):
		self.gen(pos + 1, word, rack, score, multipliers, new_arc)

board = None
gaddag = None

parser = argparse.ArgumentParser()
parser.add_argument("-d", default="words", help="word list", required=False)
parser.add_argument("board", help="board")
parser.add_argument("-W", help="dump GADDAG as dot graph", required=False)
args = parser.parse_args()

gaddag = GADDAG(args.d)
if args.W:
    gaddag.dump(args.W)
    sys.exit(0)

board = Board(args.board)

n = Solver(board, gaddag)
n.solve()
