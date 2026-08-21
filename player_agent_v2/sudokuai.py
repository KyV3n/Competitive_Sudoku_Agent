import random
import copy
import time
import competitive_sudoku.sudokuai
from math import inf
from competitive_sudoku.sudoku import GameState, Move, SudokuBoard
from typing import List, Tuple, Optional, Iterator
from collections import Counter

Square = Tuple[int, int]

class SudokuAI(competitive_sudoku.sudokuai.SudokuAI):
    """
    Competitive Sudoku AI using heuristic move selection and minimax with alpha-beta pruning.
    """
    def __init__(self):
        super().__init__()

    # =============================================================
    # Main function to run
    # =============================================================
    def compute_best_move(self, game_state: GameState) -> None:
        """
        Compute the best move in a competitive sudoku game, given a certain game state.
        """
        # Initialize variables
        start_time = time.time()
        time_limit = 0.9                    # Time limit for computation

        N = game_state.board.N              # NxN board
        total_spaces = N * N
        empty_spaces = total_spaces - len(game_state.moves)
        # empty_spaces = total_spaces - len(game_state.moves) + len(game_state.taboo_moves)

        # Keep track of who your agent is playing as for the Minimax (whose perspective you measure from)
        my_agent_id = game_state.current_player

        # Maximum MiniMax search depth based on the number of empty spaces
        # TODO: Test what is a good maximum depth
        if empty_spaces > (total_spaces * 0.7):
            minimax_depth = 1
        elif empty_spaces > (total_spaces * 0.4):
            minimax_depth = 2
        elif empty_spaces > (total_spaces * 0.2):
            minimax_depth = 3
        else:
            minimax_depth = 4

        # ---------------------------------------------------------
        # Generate candidate squares using heuristics for better Minimax search
        # ---------------------------------------------------------
        # All squares where the current player is allowed to play
        candidate_squares = game_state.player_squares()
        if not candidate_squares:
            return
        random.shuffle(candidate_squares)

        # Find squares that both players can reach
        shared_squares = self.get_shared_squares(game_state)
        shared_set = set(shared_squares)

        # Prioritize squares that complete a row, column or block
        scoring_squares = self.find_scoring_squares(candidate_squares, game_state)

        scoring_shared_squares = [square for square in scoring_squares if square in shared_set]
        scoring_candidate_squares = [square for square in scoring_squares if square not in shared_set]

        scoring_set = set(scoring_shared_squares) | set(scoring_candidate_squares)
        remaining_candidates = [square for square in candidate_squares if square not in scoring_set]

        # Final Minimax search order:
        # 1. Scoring squares that are shared with the opponent
        # 2. Other scoring squares
        # 3. All remaining candidate squares
        candidates = scoring_shared_squares + scoring_candidate_squares + remaining_candidates

        if not candidates:
            return

        # Propose a random move before starting the algorithm (prevent time-out without making a move)
        best_move = None
        best_value = -float("inf")

        fallback_square = candidates[0]
        fallback_value = self.find_random_valid_value(game_state, fallback_square)

        if fallback_value is not None:
            best_move = Move(fallback_square, fallback_value)
            self.propose_move(best_move)

        # ---------------------------------------------------------
        # Minimax search
        # ---------------------------------------------------------
        for candidate_square in candidates:
            # Time constraint
            if time.time() - start_time > time_limit:
                break  # Time limit exceeded

            # Find a legal value for this square
            candidate_value = self.find_random_valid_value(game_state, candidate_square)
            if candidate_value is None:
                continue

            # Make move and update board state
            move = Move(candidate_square, candidate_value)
            child_state = self.apply_move_search(game_state, move)

            # Search the branch (simulated future position) for an evaluation value
            value = self.minimax(child_state, depth=minimax_depth - 1, alpha=-float("inf"), beta=float("inf"),
                                       maximizing=False, start_time=start_time, time_limit=time_limit, my_agent_id=my_agent_id)

            # Keep the best move from my_agent perspective
            if value > best_value:
                best_value = value
                best_move = move
                self.propose_move(best_move)

        # No legal move was found
        if best_move is None:
            return

    # =============================================================
    # Minimax
    # =============================================================
    def minimax(self, state: GameState, depth: int, alpha: float, beta: float, maximizing: bool, start_time: float,
                           time_limit: float, my_agent_id: int) -> float:
        """
        Standard minimax algorithm with alpha-beta pruning.
        """
        # Stopping condition: Check for time limit
        if time.time() - start_time > time_limit:
            return self.evaluate_state(state, my_agent_id)

        # Stopping condition: Check for leaf node (depth reached)
        if depth == 0:
            return self.evaluate_state(state, my_agent_id)

        # Generate legal candidate squares
        candidate_squares = state.player_squares()
        if not candidate_squares:
            return self.evaluate_state(state, my_agent_id)

        # TODO: Ideally we would want to have a deterministic ordering here
        random.shuffle(candidate_squares)

        # MAX node
        if maximizing:
            value = -inf
            for candidate_square in candidate_squares:
                if time.time() - start_time > time_limit:
                    break

                candidate_value = self.find_random_valid_value(state, candidate_square)
                if candidate_value is None:
                    continue

                # Make move to new child state
                move = Move(candidate_square, candidate_value)
                child_state = self.apply_move_search(state, move)

                # Evaluate
                child_val = self.minimax(child_state, depth - 1, alpha, beta,
                                         maximizing=False, start_time=start_time, time_limit=time_limit, my_agent_id=my_agent_id)
                value = max(value, child_val)

                # Alpha-Beta pruning
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return value

        # MIN node
        else:
            value = inf
            for candidate_square in candidate_squares:
                # Stopping condition: Check for time limit
                if time.time() - start_time > time_limit:
                    break

                candidate_value = self.find_random_valid_value(state, candidate_square)
                if candidate_value is None:
                    continue

                # Make move to new child state
                move = Move(candidate_square, candidate_value)
                child_state = self.apply_move_search(state, move)

                # Evaluate
                child_val = self.minimax(child_state, depth - 1, alpha, beta,
                                         maximizing=True, start_time=start_time, time_limit=time_limit, my_agent_id=my_agent_id)
                value = min(value, child_val)

                # Alpha-Beta pruning
                beta = min(beta, value)
                if alpha >= beta:
                    break
            return value

    # =============================================================
    # Move simulation
    # =============================================================
    def clone_game_state(self, game_state: GameState) -> GameState:
        """
        Return a deep copy of the game state.
        """
        return copy.deepcopy(game_state)

    def apply_move_search(self, state: GameState, move: Move) -> GameState:
        """
        Simulate applying a move without modifying the original state (using a deep copy).
        """
        new_state = self.clone_game_state(state)

        square = move.square
        value = move.value

        # Put the value on the simulated board
        new_state.board.put(square, value)

        # Record the move in history (also which player occupies the square)
        new_state.moves.append(move)
        if new_state.current_player == 1:
            new_state.occupied_squares1.append(square)
        else:
            new_state.occupied_squares2.append(square)

        # Update scores for new move
        points = self.compute_local_score_for_move(new_state.board, square)
        new_state.scores[new_state.current_player - 1] += points

        # Switch player: 1 -> 2, 2 -> 1
        new_state.current_player = 3 - new_state.current_player

        return new_state

    # =============================================================
    # Sudoku rules legal moves
    # =============================================================
    def get_block_cells(self, board, square):
        """
        Return all coordinates belonging to the block containing square.
        """
        row, column = square

        block_height = board.region_height()
        block_width = board.region_width()

        start_row = (row // block_height) * block_height
        start_column = (column // block_width) * block_width

        for r in range(start_row, start_row + block_height):
            for c in range(start_column, start_column + block_width):
                yield (r, c)

    # TODO: Change this for a non-random return function
    def find_random_valid_value(self, game_state: GameState, square: Square):
        """
        Find a random legal Sudoku value for a given square.
        If several values are legal, one is chosen randomly.
        """
        board = game_state.board
        row, column = square
        N = board.N

        # Find taboo values specifically associated with this square
        taboo_moves = game_state.taboo_moves
        taboo_values = [taboo.value for taboo in taboo_moves if taboo.square == square]

        valid_values: list[int] = []
        block_cells = list(self.get_block_cells(board, square))

        # Sudoku numbers are 1...N
        for value in range(1, N + 1):
            # Taboo move
            if value in taboo_values:
                continue
            illegal = False

            # Check row and column
            for idx in range(N):
                if board.get((row, idx)) == value or board.get((idx, column)) == value:
                    illegal = True
                    break

            if illegal:
                continue

            # Check block
            for block_square in block_cells:
                if board.get(block_square) == value:
                    illegal = True
                    break

            if not illegal:
                valid_values.append(value)

        if not valid_values:
            return None  # or raise RuntimeError("No valid value for square")

        return random.choice(valid_values)

    # =============================================================
    # Scoring
    # =============================================================
    def compute_local_score_for_move(self, board, square):
        """
        Calculates the points scored for a particular move.
        This is based on whether the move completed a region (row, column or block).
            0 regions -> 0 points
            1 region  -> 1 point
            2 regions -> 3 points
            3 regions -> 7 points
        """
        row, column = square
        N = board.N
        EMPTY = SudokuBoard.empty

        completed = 0

        # Row scoring
        row_full = True
        for col in range(N):
            # Any cell in the move's row is still empty
            if board.get((row, col)) == EMPTY:
                row_full = False
                break
        if row_full:
            completed += 1

        # Column scoring
        col_full = True
        for row in range(N):
            # Any cell in the move's column is still empty
            if board.get((row, column)) == EMPTY:
                col_full = False
                break
        if col_full:
            completed += 1

        # Block scoring
        block_full = all(board.get(block_square) != EMPTY for block_square in self.get_block_cells(board, square))
        if block_full:
            completed += 1

        if completed == 0:
            return 0
        elif completed == 1:
            return 1
        elif completed == 2:
            return 3
        elif completed == 3:
            return 7

    # =============================================================
    # Terminal state evaluation
    # =============================================================
    def evaluate_state(self, state: GameState, my_agent_id: int) -> float:
        """
        Evaluate the current (terminal) state based on score and available moves (as a heuristic).
        """
        # Current scores
        my_score = state.scores[my_agent_id - 1]
        opp_score = state.scores[2 - my_agent_id]

        # Available moves
        my_area = self.get_playable_squares(state, my_agent_id) or []
        opp_area = self.get_playable_squares(state, 3 - my_agent_id) or []

        # Actual points are more important than territory
        # TODO: More carefully selected evaluation system
        return (my_score - opp_score) * 12 + (len(my_area) - len(opp_area))


    def get_playable_squares(self, game_state: GameState, player: int) -> Optional[List[Square]]:
        """
        Return the list of squares where the player can play.
        It is a copy of the player_squares(self) function in the GameState class.
        """
        allowed_squares = game_state.allowed_squares1 if player == 1 else game_state.allowed_squares2
        occupied_squares = game_state.occupied_squares1 if player == 1 else game_state.occupied_squares2
        N = game_state.board.N

        if allowed_squares is None:
            return None

        def is_empty(square: Square) -> bool:
            return game_state.board.get(square) == SudokuBoard.empty

        # Find valid neighbours of a given square
        def neighbors(square: Square) -> Iterator[Square]:
            row, col = square

            # Neighbouring squares are either -1, 0, or 1 away both vertically and horizontally
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:  # if it is the same square as the one given
                        continue
                    r, c = row + dr, col + dc  # (r,c) coordinates of neighbouring square
                    if 0 <= r < N and 0 <= c < N:
                        yield r, c

        # Add the empty allowed squares
        result = [s for s in allowed_squares if is_empty(s)]

        # Add the empty neighbors to result
        for s1 in occupied_squares:
            for s2 in neighbors(s1):
                if is_empty(s2):
                    result.append(s2)

        # Remove duplicates
        return sorted(list(set(result)))

    # =============================================================
    # Move prioritization (heuristics)
    # =============================================================
    def get_shared_squares(self, game_state: GameState) -> Optional[List[Square]]:
        """
        Return squares that both players can currently reach
        """
        player1_squares = (self.get_playable_squares(game_state, 1) or [])
        player2_squares = (self.get_playable_squares(game_state, 2) or [])

        player2_set = set(player2_squares)

        shared_squares = [square for square in player1_squares if square in player2_set]
        return shared_squares

    def find_columns_with_single_empty(self, game_state: GameState) -> List[Square]:
        """
        Find columns containing exactly one empty square.
        """
        board = game_state.board
        N = board.N

        columns_with_single_empty: List[Square] = []

        for column in range(N):
            empty_count = 0
            empty_square: Square | None = None

            for row in range(N):  # j is the row
                if board.get((row,column)) == SudokuBoard.empty:
                    empty_count += 1
                    empty_square = (row,column)
                    if empty_count > 1:
                        break

            if empty_count == 1 and empty_square is not None:
                columns_with_single_empty.append(empty_square)

        return columns_with_single_empty

    def find_rows_with_single_empty(self, game_state: GameState) -> List[Square]:
        """
        Find rows containing exactly one empty square
        """
        board = game_state.board
        N = board.N

        rows_with_single_empty: List[Square] = []

        for row in range(N):
            empty_count = 0
            empty_square: Square | None = None

            for column in range(N):
                if board.get((row, column)) == SudokuBoard.empty:
                    empty_count += 1
                    empty_square = (row, column)
                    if empty_count > 1:
                        break

            if empty_count == 1 and empty_square is not None:
                rows_with_single_empty.append(empty_square)

        return rows_with_single_empty

    def find_blocks_with_single_empty(self, game_state: GameState) -> List[Square]:
        """
        Find blocks containing exactly one empty square
        """
        board = game_state.board
        N = board.N

        block_height = board.region_height()
        block_width = board.region_width()

        result = []

        # Loop over each block origin
        for block_start_row in range(0, N, block_height):   # block start row
            for block_start_column in range(0, N, block_width):  # block start col
                empty_count = 0
                empty_square = None

                for row in range(block_start_row, block_start_row + block_height):
                    for column in range(block_start_column, block_start_column + block_width):

                        if board.get((row, column)) == SudokuBoard.empty:
                            empty_count += 1
                            empty_square = (row, column)
                            if empty_count > 1:
                                break

                    if empty_count > 1:
                        break

                if empty_count == 1:
                    result.append(empty_square)

        return result

    def find_scoring_squares(self, candidates: List[Square], game_state :GameState):
        """
        Prioritize candidate squares that would complete a row, column, or block.
        If a square completes multiple regions, it receives a higher priority.
        """
        single_columns = self.find_columns_with_single_empty(game_state)
        single_rows = self.find_rows_with_single_empty(game_state)
        single_blocks = self.find_blocks_with_single_empty(game_state)

        # A square may appear in multiple lists if it completes multiple regions
        scoring_squares = single_columns + single_rows + single_blocks
        if not scoring_squares:
            return []

        # Count how many regions each square would complete
        region_counts = Counter(m for m in scoring_squares)
        candidate_set = set(candidates)
        scoring_candidates = [square for square in scoring_squares if square in candidate_set]

        # Highest scoring squares first
        scoring_candidates.sort(
            key=lambda square: region_counts[square],
            reverse=True
        )

        return scoring_candidates