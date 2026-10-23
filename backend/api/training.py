import chess


def _position(moves):
	board = chess.Board()
	for san in moves:
		board.push_san(san)
	return board


LESSONS = [
	{
		'id': 'mate-fundamentals',
		'level': 1,
		'level_title': 'Beginner',
		'title': 'Spot a simple checkmate',
		'theme': 'king safety',
		'objective': 'Recognize a direct mating attack and verify that the king has no safe escape.',
		'steps': [
			'Look at the opponent king and list every square it could escape to.',
			'Find a forcing check that the king cannot capture or block.',
			'Before moving, confirm that every escape square is covered.',
		],
		'hints': [
			'Start with checks: which of your pieces can attack the king immediately?',
			'Look at the queen and bishop working together near f7.',
			'Can the queen capture the pawn beside the king with support?',
		],
		'feedback': 'Check every forcing move first. A check that removes all king escapes is the goal.',
		'setup': ('e4', 'e5', 'Qh5', 'Nc6', 'Bc4', 'Nf6'),
		'solution': 'h5f7',
		'explanation': 'Qxf7 is checkmate: the queen is protected by the bishop and the king has no escape.',
	},
	{
		'id': 'loose-piece-scan',
		'level': 1,
		'level_title': 'Beginner',
		'title': 'Notice an undefended queen',
		'theme': 'piece safety',
		'objective': 'Scan for valuable enemy pieces that are not protected before choosing a move.',
		'steps': [
			'Check whether your king is safe and whether any of your pieces are attacked.',
			'Look for an opponent piece that can be captured without losing your attacker.',
			'After the capture, check whether the opponent has a forcing reply.',
		],
		'hints': [
			'Compare the long rook file with the queen on the corner square.',
			'The path from your rook to the queen is clear.',
			'Capture the queen with your rook.',
		],
		'feedback': 'Look for an undefended valuable piece, then check that your capturing piece is safe.',
		'fen': 'q7/4k3/8/8/8/8/8/R3K3 w - - 0 1',
		'solution': 'a1a8',
		'explanation': 'Rxa8 wins the undefended queen. Always scan for loose pieces before making a quiet move.',
	},
	{
		'id': 'knight-fork',
		'level': 2,
		'level_title': 'Developing Player',
		'title': 'Fork two valuable pieces',
		'theme': 'fork',
		'objective': 'Use a knight to attack two valuable targets at once.',
		'steps': [
			'Find a move that creates two threats with one piece.',
			'Check every square the knight attacks after it moves.',
			'Make sure the opponent cannot save both targets in one move.',
		],
		'hints': [
			'Look for a knight jump that attacks more than one major piece.',
			'The knight can attack the queen on f6 and rook on b6 from the same square.',
			'Move the c3 knight to d5.',
		],
		'feedback': 'A fork creates two threats at once. Trace the knight attacks after each candidate jump.',
		'fen': '8/7k/2r5/5q2/8/1N6/K7/8 w - - 0 1',
		'solution': 'b3d4',
		'explanation': 'Nd5 attacks both the queen on f6 and rook on b6. The opponent cannot protect both targets at once.',
	},
	{
		'id': 'back-rank-mate',
		'level': 2,
		'level_title': 'Developing Player',
		'title': 'Punish a blocked back rank',
		'theme': 'back-rank mate',
		'objective': 'Recognize when a king trapped behind its own pawns has no escape.',
		'steps': [
			'Check whether the king has an empty flight square.',
			'Look for a rook or queen that can enter the king’s rank.',
			'Verify that the king cannot capture, block, or escape the check.',
		],
		'hints': [
			'The black king is boxed in by its own pawns.',
			'The e-file is open for your rook.',
			'Move the rook to the eighth rank with check.',
		],
		'feedback': 'Look for a heavy piece entering the back rank while the king has no flight square.',
		'fen': '6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1',
		'solution': 'e1e8',
		'explanation': 'Re8 is checkmate. The rook attacks across the eighth rank, and the king’s own pawns block its escape.',
	},
	{
		'id': 'mating-net',
		'level': 3,
		'level_title': 'Intermediate',
		'title': 'Build a protected mating net',
		'theme': 'king safety',
		'objective': 'Coordinate queen and rook so the checking piece is protected.',
		'steps': [
			'Find a forcing queen check close to the king.',
			'Check whether the king can capture the queen.',
			'Use your rook’s line to confirm the queen is defended.',
		],
		'hints': [
			'The queen is close to the black king and can capture a pawn.',
			'Look at the rook’s line up the h-file.',
			'Capture the h7 pawn with the queen.',
		],
		'feedback': 'A mating net needs both a check and coverage of every escape square.',
		'fen': '7k/6pp/6Q1/8/8/8/8/K6R w - - 0 1',
		'solution': 'g6h7',
		'explanation': 'Qxh7 is mate. The rook protects the queen, while the queen covers the king’s escape squares.',
	},
	{
		'id': 'promotion-basics',
		'level': 3,
		'level_title': 'Intermediate',
		'title': 'Promote a passed pawn',
		'theme': 'endgame',
		'objective': 'Advance a passed pawn to promotion and choose the strongest piece.',
		'steps': [
			'Check whether the pawn’s path to the last rank is clear.',
			'Calculate whether the opposing king can stop it.',
			'Promote to a queen unless a special position requires another piece.',
		],
		'hints': [
			'Your passed pawn is one step from the last rank.',
			'The black king is too far away to stop promotion.',
			'Advance the pawn and promote it to a queen.',
		],
		'feedback': 'Count the pawn’s steps to promotion and compare them with the opposing king’s distance.',
		'fen': '8/4P3/8/8/8/8/4k3/K7 w - - 0 1',
		'solution': 'e7e8q',
		'explanation': 'e8=Q+ promotes the passed pawn with check. In most positions, a queen is the strongest promotion.',
	},
	{
		'id': 'king-safety-calculation',
		'level': 4,
		'level_title': 'Advanced',
		'title': 'Calculate a forcing king attack',
		'theme': 'king safety',
		'objective': 'Calculate a forcing sequence and recognize how weakened king cover creates a mating threat.',
		'steps': [
			'Identify the king’s weakened squares and open diagonals.',
			'Consider checks before captures and quiet moves.',
			'Verify the opponent’s legal replies after your forcing move.',
		],
		'hints': [
			'White’s last pawn moves have opened the diagonal to the king.',
			'Find the queen move that checks along that diagonal.',
			'Move the queen from d8 to h4.',
		],
		'feedback': 'When the king is exposed, search checks first and calculate the reply to each one.',
		'setup': ('f3', 'e5', 'g4'),
		'side_to_move': 'black',
		'solution': 'd8h4',
		'explanation': 'Qh4 is checkmate: the queen checks along the diagonal and White’s own pawns block the king.',
	},
	{
		'id': 'rook-scan-variation',
		'level': 4,
		'level_title': 'Advanced',
		'title': 'Recheck the whole board',
		'theme': 'piece safety',
		'objective': 'Use a full-board scan to find a valuable target outside the area of immediate action.',
		'steps': [
			'Look at every open rank, file, and diagonal.',
			'Check whether a valuable piece is defended.',
			'Capture only after confirming your own king remains safe.',
		],
		'hints': [
			'The rook and queen share an open file.',
			'The queen has no defender on that file.',
			'Capture the queen with the rook.',
		],
		'feedback': 'Do not focus only on the center. Scan open files for undefended targets.',
		'fen': '7q/k7/8/8/8/8/8/4K2R w - - 0 1',
		'solution': 'h1h8',
		'explanation': 'Rxh8 wins the undefended queen. A quick scan of every open file can reveal material left en prise.',
	},
	{
		'id': 'expert-fork-calculation',
		'level': 5,
		'level_title': 'Expert',
		'title': 'Calculate a knight fork',
		'theme': 'calculation',
		'objective': 'Find the knight move that creates two independent threats against major pieces.',
		'steps': [
			'List forcing candidate moves, beginning with checks and attacks.',
			'For each knight move, trace all attacked enemy pieces.',
			'Calculate whether the opponent can save both targets.',
		],
		'hints': [
			'A knight can attack the queen and rook from one square.',
			'Look at the squares attacked by a knight on f7.',
			'Move the knight from g5 to f7.',
		],
		'feedback': 'Compare candidate knight jumps by counting how many valuable targets they attack.',
		'fen': '3qk2r/8/8/6N1/8/8/8/K7 w - - 0 1',
		'solution': 'g5f7',
		'explanation': 'Nf7 creates a fork: the knight attacks both the queen and rook from f7.',
	},
	{
		'id': 'expert-mating-net',
		'level': 5,
		'level_title': 'Expert',
		'title': 'Finish with a protected mating net',
		'theme': 'calculation',
		'objective': 'Calculate a protected queen sacrifice to close every king escape square.',
		'steps': [
			'Find the queen check next to the opposing king.',
			'Check whether the king can capture the queen.',
			'Confirm your rook protects the queen and the king has no escape.',
		],
		'hints': [
			'Your queen can capture the pawn beside the king.',
			'The rook on the a-file protects the destination square.',
			'Move the queen from b6 to a7.',
		],
		'feedback': 'Before playing a mating move, verify the checking piece is protected and every flight square is covered.',
		'fen': 'k7/pp6/1Q6/8/8/8/8/R6K w - - 0 1',
		'solution': 'b6a7',
		'explanation': 'Qxa7 is checkmate. The rook protects the queen, and the queen controls the king’s remaining escape squares.',
	},
]

LEVEL_TITLES = {
	1: 'Beginner',
	2: 'Developing Player',
	3: 'Intermediate',
	4: 'Advanced',
	5: 'Expert',
}


def _additional_lesson(level, slug, title, theme, setup, solution, explanation, first_hint, second_hint):
	board = _position(setup)
	move = chess.Move.from_uci(solution)
	return {
		'id': slug,
		'level': level,
		'level_title': LEVEL_TITLES[level],
		'title': title,
		'theme': theme,
		'objective': f'Learn {theme} by finding the key move in this position.',
		'steps': [
			'Look at the whole board and identify the most important threat.',
			f'Use the position to practice {theme}.',
			'Check that your move is legal and achieves the lesson goal.',
		],
		'hints': [
			first_hint,
			second_hint,
			f'Try {board.san(move)}.',
		],
		'feedback': f'Look carefully for the key idea in {theme} before you move.',
		'setup': setup,
		'solution': solution,
		'explanation': explanation,
	}


def _custom_fen_lesson(level, slug, title, theme, fen, solution, explanation, first_hint, second_hint):
	board = chess.Board(fen)
	move = chess.Move.from_uci(solution)
	return {
		'id': slug,
		'level': level,
		'level_title': LEVEL_TITLES[level],
		'title': title,
		'theme': theme,
		'objective': f'Learn {theme} by finding the key move in this position.',
		'steps': [
			'Look at the whole board and identify the most important threat.',
			f'Use the position to practice {theme}.',
			'Check that your move is legal and achieves the lesson goal.',
		],
		'hints': [
			first_hint,
			second_hint,
			f'Try {board.san(move)}.',
		],
		'feedback': f'Look carefully for the key idea in {theme} before you move.',
		'fen': board.fen(),
		'side_to_move': 'black' if board.turn == chess.BLACK else 'white',
		'solution': move.uci(),
		'explanation': explanation,
	}


def _transform_square(square, transform):
	file_index = chess.square_file(square)
	rank_index = chess.square_rank(square)
	if transform == 'mirror_files':
		file_index = 7 - file_index
	elif transform == 'mirror_ranks':
		rank_index = 7 - rank_index
	elif transform == 'rotate':
		file_index, rank_index = 7 - file_index, 7 - rank_index
	elif transform == 'transpose':
		file_index, rank_index = rank_index, file_index
	elif transform == 'anti_transpose':
		file_index, rank_index = 7 - rank_index, 7 - file_index
	elif transform == 'shift_right':
		file_index += 1
	elif transform == 'shift_left':
		file_index -= 1
	elif transform == 'shift_up':
		rank_index += 1
	elif transform == 'shift_down':
		rank_index -= 1
	elif transform == 'mirror_files_shift_up':
		file_index, rank_index = 7 - file_index, rank_index + 1
	elif transform == 'mirror_files_shift_down':
		file_index, rank_index = 7 - file_index, rank_index - 1
	return chess.square(file_index, rank_index)


def _lesson_variant(source_id, level, slug, title, theme, transform, explanation, first_hint, second_hint):
	source = next(lesson for lesson in LESSONS if lesson['id'] == source_id)
	board = chess.Board(source['fen']) if 'fen' in source else _position(source['setup'])
	if transform in {'mirror_ranks', 'rotate'}:
		board = board.mirror()
		if transform == 'rotate':
			board.apply_transform(lambda bitboard: sum(
				chess.BB_SQUARES[_transform_square(square, 'mirror_files')]
				for square in chess.scan_forward(bitboard)
			))
	else:
		board.apply_transform(lambda bitboard: sum(
			chess.BB_SQUARES[_transform_square(square, transform)]
			for square in chess.scan_forward(bitboard)
		))
	source_move = chess.Move.from_uci(source['solution'])
	move = chess.Move(
		_transform_square(source_move.from_square, transform),
		_transform_square(source_move.to_square, transform),
		promotion=source_move.promotion,
	)
	return {
		'id': slug,
		'level': level,
		'level_title': LEVEL_TITLES[level],
		'title': title,
		'theme': theme,
		'objective': f'Learn {theme} by finding the key move in this position.',
		'steps': [
			'Look at the whole board and identify the most important threat.',
			f'Use the position to practice {theme}.',
			'Check that your move is legal and achieves the lesson goal.',
		],
		'hints': [
			first_hint,
			second_hint,
			f'Try {board.san(move)}.',
		],
		'feedback': f'Look carefully for the key idea in {theme} before you move.',
		'fen': board.fen(),
		'side_to_move': 'black' if board.turn == chess.BLACK else 'white',
		'solution': move.uci(),
		'explanation': explanation,
	}


ADDITIONAL_LESSONS = [
	_additional_lesson(1, 'center-pawn-e4', 'Take space in the center', 'opening principles', (), 'e2e4',
		'e4 claims central space and opens lines for the queen and bishop.',
		'The four central squares are the heart of the board.', 'Choose the king pawn.'),
	_additional_lesson(1, 'center-pawn-d4', 'Build a second center', 'opening principles', (), 'd2d4',
		'd4 controls central squares and opens a path for the queen-side bishop.',
		'Think about controlling the center with a pawn.', 'Choose the queen pawn.'),
	_additional_lesson(1, 'develop-knight-f3', 'Bring out a knight', 'piece development', ('e4', 'e5'), 'g1f3',
		'Nf3 develops a piece toward the center and attacks the e5 pawn.',
		'Develop a minor piece before bringing the queen out.', 'Move the king-side knight toward the center.'),
	_additional_lesson(1, 'develop-knight-c3', 'Develop your other knight', 'piece development', ('e4', 'e5', 'Nf3', 'Nc6'), 'b1c3',
		'Nc3 develops the second knight and adds control over d5 and e4.',
		'Find the undeveloped knight.', 'Move the queen-side knight toward the center.'),
	_additional_lesson(1, 'develop-bishop-c4', 'Aim your bishop at the center', 'piece development', ('e4', 'e5', 'Nf3', 'Nc6'), 'f1c4',
		'Bc4 develops the bishop and points toward the f7 square beside the king.',
		'Move a bishop to an active diagonal.', 'The bishop on f1 has a clear diagonal toward c4.'),
	_additional_lesson(1, 'capture-center-pawn', 'Capture a central pawn', 'safe captures', ('e4', 'd5', 'Nc3', 'Nf6'), 'e4d5',
		'exd5 captures the pawn that advanced into the center. Always check how the opponent can recapture.',
		'One of your pawns can capture the black pawn in the center.', 'Use the e-pawn to take the pawn on d5.'),
	_additional_lesson(1, 'castle-to-safety', 'Castle your king to safety', 'king safety', ('e4', 'e5', 'Nf3', 'Nc6', 'Bc4', 'Nf6'), 'e1g1',
		'Castling moves the king away from the center and brings the rook into play.',
		'Your king and rook can make one special move together.', 'Choose the short castle.'),
	_additional_lesson(1, 'develop-bishop-g5', 'Develop with a useful pin', 'piece development', ('d4', 'd5', 'c4', 'e6', 'Nc3', 'Nf6'), 'c1g5',
		'Bg5 develops the bishop and pressures the knight in front of the black queen.',
		'Look for an active bishop diagonal.', 'Move the queen-side bishop to g5.'),

	_lesson_variant('knight-fork', 2, 'fork-practice-one', 'Fork two targets', 'knight fork', 'mirror_files',
		'A knight fork attacks two valuable pieces at once.',
		'Look for a knight jump that attacks two targets.', 'Check which squares the knight attacks after it moves.'),
	_lesson_variant('knight-fork', 2, 'fork-practice-two', 'Find a second fork', 'knight fork', 'mirror_ranks',
		'The knight lands with tempo and attacks two valuable targets.',
		'Search for a forcing knight move.', 'The best landing square attacks both the queen and rook.'),
	_lesson_variant('knight-fork', 2, 'fork-practice-three', 'Fork from a new angle', 'knight fork', 'rotate',
		'The same fork idea works from either side of the board.',
		'List the squares the knight can reach.', 'Choose the square from which it attacks both major pieces.'),
	_lesson_variant('knight-fork', 2, 'fork-practice-four', 'Spot the double attack', 'double attack', 'transpose',
		'One move creates two threats that cannot both be answered.',
		'Look for one move that creates two separate problems.', 'Use the knight to attack both major pieces.'),
	_additional_lesson(2, 'pin-the-knight', 'Pin a defender to its king', 'pin', ('e4', 'e5', 'Nf3', 'Nc6', 'Bc4', 'Nf6'), 'c4b5',
		'Bb5 pins the knight on c6 to the king on e8 along the diagonal.',
		'Find a bishop move that lines up with the king.', 'Move the bishop from c4 to b5.'),
	_additional_lesson(2, 'pin-the-knight-again', 'Use a pin to build pressure', 'pin', ('e4', 'e5', 'Nf3', 'Nc6', 'd4', 'exd4'), 'f1b5',
		'Bb5+ pins the knight on c6 to the king on e8 and creates a forcing check.',
		'Find a bishop move that checks along the diagonal through the knight.', 'Move the bishop from f1 to b5.'),
	_lesson_variant('back-rank-mate', 2, 'back-rank-practice', 'Find the back-rank finish', 'back-rank mate', 'mirror_files',
		'The rook mates because the king is trapped behind its own pawns.',
		'Count the king’s safe escape squares.', 'Bring the rook to the eighth rank with check.'),
	_lesson_variant('loose-piece-scan', 2, 'loose-queen-practice', 'Win an undefended queen', 'piece safety', 'mirror_files',
		'The rook can capture the queen along the open back rank.',
		'Scan the open rank for a valuable target.', 'Capture the queen with the rook.'),

	_lesson_variant('promotion-basics', 3, 'promotion-practice-one', 'Promote a passed pawn', 'pawn promotion', 'mirror_files',
		'A passed pawn can become a queen when it reaches the last rank.',
		'Count how many squares remain before promotion.', 'Advance the pawn and promote it to a queen.'),
	_lesson_variant('promotion-basics', 3, 'promotion-practice-two', 'Promote with check', 'pawn promotion', 'mirror_ranks',
		'Promotion can also give check and force the opponent to respond.',
		'Check whether the promotion move attacks the king.', 'Advance the pawn to the last rank and choose a queen.'),
	_lesson_variant('promotion-basics', 3, 'promotion-practice-three', 'Calculate the promotion square', 'endgame', 'rotate',
		'The king is too far away to stop the pawn from promoting.',
		'Compare the pawn’s distance with the opposing king.', 'Push the pawn to its final rank.'),
	_custom_fen_lesson(3, 'mating-net-practice-one', 'Close the king’s escape squares', 'mating attack',
		'6k1/5pp1/5Q2/8/8/8/8/1K4R1 w - - 0 1', 'f6g7',
		'The queen gives mate because the rook protects it and every escape is covered.',
		'Look for a protected queen check next to the king.', 'Capture the pawn beside the king with your queen.'),
	_lesson_variant('mating-net', 3, 'mating-net-practice-two', 'Finish with a protected queen', 'mating attack', 'mirror_ranks',
		'A protected queen delivers the final check with no escape.',
		'Check whether the king can capture your queen.', 'Use the queen to take the pawn beside the king.'),
	_lesson_variant('rook-scan-variation', 3, 'rook-capture-practice', 'Find the loose queen on the file', 'rook tactics', 'mirror_files',
		'The rook travels along the open file to capture the undefended queen.',
		'Trace the open file from your rook.', 'Capture the queen on the far end of the file.'),
	_lesson_variant('knight-fork', 3, 'calculated-fork', 'Calculate before you fork', 'calculation', 'anti_transpose',
		'Calculate the knight’s landing square and confirm that both targets are attacked.',
		'Do not move until you have counted the knight’s targets.', 'Choose the fork that attacks the queen and rook.'),
	_lesson_variant('back-rank-mate', 3, 'back-rank-calculation', 'Calculate the rook’s check', 'checkmate', 'rotate',
		'The back-rank rook move is mate because every escape square is blocked.',
		'Check every escape square before moving.', 'Place the rook on the back rank with check.'),

	_lesson_variant('king-safety-calculation', 4, 'queen-mate-calculation', 'Calculate the queen’s diagonal check', 'calculation', 'mirror_files',
		'The queen’s diagonal check is mate because the opposing pawns block every escape.',
		'Look for a queen check along the opened diagonal.', 'Move the queen along the diagonal to h4.'),
	_lesson_variant('king-safety-calculation', 4, 'queen-mate-calculation-two', 'Verify a forced checkmate', 'calculation', 'mirror_ranks',
		'Before playing a forcing check, verify the opponent has no legal reply.',
		'Search checks first, then test each king escape.', 'Move the queen to the checking square on the diagonal.'),
	_lesson_variant('rook-scan-variation', 4, 'rook-skewer-practice-one', 'Find the open-file tactic', 'rook tactics', 'mirror_ranks',
		'The open file lets the rook take a major piece immediately.',
		'Scan every open line for a loose target.', 'Capture the queen with your rook.'),
	_lesson_variant('rook-scan-variation', 4, 'rook-skewer-practice-two', 'Recheck the long diagonal', 'board vision', 'rotate',
		'A full-board scan reveals a valuable undefended piece.',
		'Do not focus only on the center of the board.', 'Use the rook to capture the undefended queen.'),
	_lesson_variant('knight-fork', 4, 'advanced-fork-one', 'Calculate a forcing double attack', 'calculation', 'shift_right',
		'The knight fork is forcing: the opponent cannot save both major pieces.',
		'Compare the opponent’s possible replies.', 'Move the knight to the square attacking both targets.'),
	_lesson_variant('knight-fork', 4, 'advanced-fork-two', 'Choose the strongest fork square', 'double attack', 'shift_left',
		'The strongest fork wins material because both threats arrive together.',
		'Find a knight move that attacks two valuable pieces.', 'Use the knight to attack both major pieces.'),
	_lesson_variant('promotion-basics', 4, 'promotion-calculation', 'Calculate a promotion race', 'endgame calculation', 'shift_right',
		'The passed pawn promotes before the opposing king can reach it.',
		'Count the king’s moves to the promotion square.', 'Advance the pawn and promote.'),
	_custom_fen_lesson(4, 'protected-mate-calculation', 'Verify the protected mating move', 'mating attack',
		'2k5/1pp5/1Q6/8/8/8/8/2R4K w - - 0 1', 'b6c7',
		'The checking queen is protected, and the king has no safe square.',
		'Check whether the queen can be captured.', 'Capture the pawn beside the king with your queen.'),

	_lesson_variant('knight-fork', 5, 'expert-fork-variation-one', 'Calculate both fork targets', 'advanced calculation', 'shift_up',
		'The knight fork creates two independent threats against major pieces.',
		'Map every square the knight attacks from the candidate square.', 'Place the knight on the square attacking both targets.'),
	_lesson_variant('knight-fork', 5, 'expert-fork-variation-two', 'Find the forcing knight move', 'advanced calculation', 'shift_down',
		'A forcing fork leaves the opponent unable to defend both targets.',
		'Start with forcing moves and count the attacked pieces.', 'Choose the knight move that attacks the queen and rook.'),
	_lesson_variant('knight-fork', 5, 'expert-fork-variation-three', 'Compare candidate fork squares', 'calculation', 'mirror_files_shift_up',
		'The correct landing square creates the strongest double threat.',
		'Compare each legal knight move by the threats it creates.', 'Move the knight to the fork square.'),
	_lesson_variant('knight-fork', 5, 'expert-fork-variation-four', 'Calculate the material gain', 'tactical calculation', 'mirror_files_shift_down',
		'The fork wins material because the opponent cannot move both targets.',
		'Calculate what the opponent can save after the fork.', 'Attack both major pieces with one knight move.'),
	_custom_fen_lesson(5, 'expert-mating-net-variation-one', 'Close the final mating net', 'mating calculation',
		'4k3/3pp3/3Q4/8/8/8/8/4R2K w - - 0 1', 'd6e7',
		'The queen gives mate because the rook protects it and the king has no flight square.',
		'Check the queen’s protection and every king escape.', 'Capture the pawn beside the king with your queen.'),
	_lesson_variant('expert-mating-net', 5, 'expert-mating-net-variation-two', 'Verify the final mating move', 'mating calculation', 'mirror_ranks',
		'A mating move must be protected and cover every escape square.',
		'First verify that the king cannot capture the queen.', 'Use the queen to take the pawn beside the king.'),
	_custom_fen_lesson(5, 'expert-back-rank-mate', 'Find the forced back-rank mate', 'forced checkmate',
		'6k1/5ppp/8/8/8/8/8/R6K w - - 0 1', 'a1a8',
		'The rook check is mate because the king’s own pawns block the escape squares.',
		'Calculate every possible king response.', 'Move the rook to the back rank with check.'),
	_lesson_variant('loose-piece-scan', 5, 'expert-rook-capture', 'Spot the undefended major piece', 'board-wide calculation', 'rotate',
		'The rook can capture the queen because the line is clear and the queen is undefended.',
		'Scan all open lines, not only the area near the kings.', 'Capture the queen with your rook.'),
]

LESSONS.extend(ADDITIONAL_LESSONS)
LESSONS.sort(key=lambda lesson: lesson['level'])


def lesson_position(lesson):
	board = chess.Board(lesson['fen']) if 'fen' in lesson else _position(lesson['setup'])
	if not board.is_valid():
		raise ValueError('Training puzzle position is invalid.')
	if lesson.get('side_to_move') == 'black':
		if board.turn != chess.BLACK:
			raise ValueError('Training puzzle must be set for Black to move.')
	elif board.turn != chess.WHITE:
		raise ValueError('Training puzzle must be set for White to move.')
	return board


def lesson_data(lesson, progress=None, unlocked=True):
	board = lesson_position(lesson)
	return {
		'id': lesson['id'],
		'level': lesson['level'],
		'level_title': lesson['level_title'],
		'title': lesson['title'],
		'theme': lesson['theme'],
		'objective': lesson['objective'],
		'steps': lesson['steps'],
		'hints': lesson['hints'],
		'fen': board.fen(),
		'side_to_move': 'black' if board.turn == chess.BLACK else 'white',
		'unlocked': unlocked,
		'completed': bool(progress and progress.completed_at),
		'attempts': progress.attempts if progress else 0,
	}
