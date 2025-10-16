import gamelib
import random
import math
import warnings
from sys import maxsize
import json


class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        self.prevscored= 0
        self.bad1= 0
        self.bad2= 0
        self.attack_stage= 0
        self.attackStyleHistory = [False, False, False, False]
        self.wallHistory = {
            "LEFT": [False, False],
            "RIGHT": [False, False]
        }
        self.effectiveCounter = [0, 0]
        self.effectiveBool = [True, True]
        self.shortest_path = 0

        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0

        self.weakWing = 0
        self.weakTally = [0, 0, 0]
        self.weakFunnel = False

        # This is a good place to do initial setup
        self.scored_on_locations = []

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.weakTally = [0, 0, 0]
        #gamelib.debug_write("OH NO\n\n", self.effectiveBool)
        if self.effectiveBool[0] == False:
            self.effectiveBool[0] = True
            self.effectiveCounter[0] -= 2
        if self.effectiveBool[1] == False:
            self.effectiveBool[1] = True
            self.effectiveCounter[1] -= 2

        spath = game_state.find_path_to_edge([11, 2])
        if spath!=None and len(spath)<50:
            self.shortest_path = 1
        else:
            self.shortest_path = 0

        self.starter_strategy(game_state)

        game_state.submit_turn()

    def starter_strategy(self, game_state):
        if(self.attack_stage!=2):
            if(self.bad1>0 or self.bad2>0):
                if(self.bad1>=self.bad2):
                    self.prevscored = 0
                    self.scored_on_locations.append([0, 0])
                else:
                    self.prevscored = 1
                    self.scored_on_locations.append([100, 1000])
                gamelib.debug_write(self.scored_on_locations)

        self.bad1, self.bad2 = 0, 0
        self.midgame(game_state)
        self.Defense(game_state, self.attack_stage>0)

        self.prevhealth = game_state.my_health
        self.scored_on_locations = []

    def midgame(self, game_state):
        self.evaluateAttackStyle(game_state)
        self.brawlerCounter(game_state)
        if self.attack_stage==1:
            self.attack(game_state)
            self.scored_on_locations = []
            turns = self.check_if_attack(game_state.get_resource(MP), game_state.enemy_health+1,game_state.turn_number, game_state)
            if(turns==1):
                self.attack_stage = 1
            else:
                self.attack_stage = 2
            return True
        else:
            if self.attack_stage==2:
                self.finish_attack(game_state)
                self.attack_stage = 0
            if(self.check_if_attack(game_state.get_resource(MP), game_state.enemy_health+1,game_state.turn_number, game_state)):
                self.prep_attack(game_state)
                self.attack_stage = 1
            #no elif because we can try attack again
        return False

    def Defense(self, game_state, attacking):
        self.manageBaseDefense(game_state)

        if self.attack_stage != 2 and self.attack_stage != 1:
            #gamelib.debug_write("SPAWNING WALL", self.attack_stage)
            self.finish_attack(game_state) #try to spawn wall there

        self.fixCriticalWalls(game_state)

        self.manageCriticalDefense(game_state)

        self.buildSupports1(game_state)

        #gamelib.debug_write("WEAK WING", self.weakWing, attacking)

        self.reinforceFunnel(game_state)

        if self.weakWing != 0:
            self.manageWingDefense(game_state, attacking)

        self.buildSupports2(game_state)

        self.upgradeSupports(game_state)

        self.spendExtraSP(game_state)

    def reinforceFunnel(self, game_state):
        #gamelib.debug_write("HEREHER", self.weakFunnel)
        if self.weakFunnel:
            upgrade_locs = [[21, 11], [24, 11], [20, 11]]
            game_state.attempt_upgrade(upgrade_locs)

            game_state.attempt_spawn(TURRET, [20, 11])
            game_state.attempt_spawn(TURRET, [20, 10])

    def buildSupports1(self, game_state):
        support_locations = [[18, 7], [18, 8], [19, 8]]
        
        for loc in support_locations:
            if game_state.get_resource(SP) > 5:
                game_state.attempt_spawn(SUPPORT, loc)
    
    def buildSupports2(self, game_state):
        support_locations = [[17, 8], [20, 9], [19, 9], [18, 9], [5, 9], [5, 10], [5, 11], [17, 6], [17, 7]]
        for loc in support_locations:
            if game_state.get_resource(SP) > 12:
                game_state.attempt_spawn(SUPPORT, loc)
    
    def upgradeSupports(self, game_state):
        support_locations = [[16, 5], [16, 6], [18, 7], [18, 8], [19, 8], [17, 6], [17, 7], [17, 8], [16, 7]]
        for loc in support_locations:
            if game_state.get_resource(SP) > 15:
                game_state.attempt_upgrade(loc)
    
    def spendExtraSP(self, game_state):
        return

    def fixCriticalWalls(self, game_state):
        critical_walls = [[0, 13], [1, 13], [25, 13], [27, 13]]
        for loc in critical_walls:
            unit = game_state.contains_stationary_unit(loc)
            if unit:
                if unit.health/unit.max_health < 0.8:
                    game_state.attempt_remove(loc)

    def manageWingDefense(self, game_state, attacking):
        if self.weakWing == 1:
            walls = [[0, 13], [1, 13], [4, 13]]
            turrs = [[3, 13], [3, 12]]
        elif self.weakWing == 2:
            #turrs = [[24, 13], [21, 12], [22, 12], [23, 12], [24, 12]] #!!
            turrs = [[24, 13]]
            walls = []
            if not attacking:
                turrs.append([26, 12])
                turrs.append([25, 12])
                walls.append([25, 13])
                walls.append([26, 13])
                walls.append([27, 13])
            #walls = [[20, 13], [21, 13], [22, 13], [23, 13], [25, 13], [27, 13], [20, 12], [20, 10], [21, 10], [22, 10]] # !!

        for tpl in walls:
            points = game_state.get_resource(SP)
            if points > 5:
                game_state.attempt_spawn(WALL, tpl)
            
        for tpl in turrs:
            points = game_state.get_resource(SP)
            if points > 7:
                game_state.attempt_spawn(TURRET, tpl)

        for tpl in walls:
            points = game_state.get_resource(SP)
            if points > 5:
                game_state.attempt_upgrade(tpl)

        for tpl in turrs:
            points = game_state.get_resource(SP)
            if points > 9:
                game_state.attempt_upgrade(tpl)

    def manageBaseDefense(self, game_state):
        self.base_walls = [[0, 13], [1, 13], [21, 13], [22, 13], [23, 13], [25, 13], [27, 13], [1, 13], [3, 12], [4, 11], [4, 10], [21, 10], [22, 10], [4, 9], [21, 9], [5, 8], [20, 8], [6, 7], [19, 7], [7, 6], [18, 6], [8, 5], [17, 5], [16, 4], [11, 4], [10, 5], [9, 5], [12, 3], [15, 3], [13, 2], [14, 2]]  # !!
        #self.base_walls= [[0, 13],[25, 13], [27, 13], [2, 11], [3, 10], [22, 10], [4, 9], [21, 9], [5, 8], [20, 8], [6, 7], [19, 7], [7, 6], [18, 6], [8, 5], [17, 5], [9, 4], [16, 4], [10, 3], [11, 3], [12, 3], [13, 2], [14, 2], [15, 3]]

        self.base_turrs= [[1, 12], [3, 13], [23, 11], [24, 13], [22, 11], [21, 11]]

        game_state.attempt_spawn(WALL, self.base_walls)
        game_state.attempt_spawn(TURRET, self.base_turrs)

    def manageCriticalDefense(self, game_state):
        critWalls = [[0, 13], [1, 13], [21, 13], [22, 13], [23, 13], [25, 13], [27, 13], [21, 10]]
        critTurrs = [[23, 12], [1, 12], [3, 13], [24, 13], [22, 11]]
        game_state.attempt_upgrade(critWalls)
        game_state.attempt_upgrade(critTurrs)
    
    def get_gain(self, rnd):
        return 5+rnd//10
    
    def prevMP(self, cur, gain, rnd):
        return (cur-self.get_gain(rnd))/0.75
    
    def get_hurt(self, val, game_state):
        return max(val-self.get_cost(game_state), 0)

    def check_if_attack(self, current_mp, current_hp, rnd, game_state):
        n_rounds = 101
        n= 32
        dp= [[[101 for k in range(n)] for j in range(n)] for i in range(n_rounds)]
        for i in range(n_rounds):
            for j in range(n):
                dp[i][j][0] = 0
        for i in range(n_rounds-2, -1, -1):
            for j in range(n):
                for k in range(n):
                    a = dp[i][j][k]
                    b = dp[i+1][min((int)(j*0.75+self.get_gain(i)), n-1)][k]+1
                    c = dp[i+1][self.get_gain(i)][max(k-self.get_hurt(j, game_state), 0)]+1
                    dp[i][j][k] = min(a, min(b, c))
        current_hp = int(current_hp)
        ta = current_mp*0.75+self.get_gain(rnd)
        ta = ta*0.75+self.get_gain(rnd+1)
        ta = min(int(ta), n-1)
        #tb = self.get_gain(rnd)*0.75+self.get_gain(rnd+1)
        #tb = int(tb)

        money_to_attack = current_mp*0.75+self.get_gain(rnd)
        gamelib.debug_write("MONEY", self.get_gain(rnd+1))
        gamelib.debug_write("MONEY", ta)
        a = dp[rnd+2][ta][current_hp]
        b = dp[rnd+2][self.get_gain(rnd+1)][max((int)(current_hp-self.get_hurt(money_to_attack, game_state)), 0)]
        gamelib.debug_write("IF ATTACK", b)
        gamelib.debug_write("IF NO ATTACK", a)
        if a<b:
            return 0
        return 1

    def get_cost(self, game_state):
        if game_state.turn_number>0:
            if self.shortest_path:
                return 5
            #gamelib.debug_write(game_state.find_path_to_edge([9, 4]))
        if self.attackStyleHistory[-1] or self.attackStyleHistory[-2] or self.attackStyleHistory[-3] or self.attackStyleHistory[-4]: 
            return 5
        else:
            return 7

    def prep_attack(self, game_state):
    
        x = game_state.attempt_remove([[26, 13], [25, 11], [25, 12], [26, 12]]); #block off ur current and then attack
        gamelib.debug_write("REMOVED ", x)

    def evaluateAttackStyle(self, game_state):
        dx = [1, -1, 0, 0]
        dy = [0, 0, 1, -1]
        locations = [[22, 19], [22, 18], [23, 18], [22, 17], [23, 17], [24, 17], [22, 16], [23, 16], [24, 16], [25, 16], [22, 15], [23, 15], [24, 15], [25, 15], [26, 15], [23, 14], [24, 14], [25, 14], [26, 14], [27, 14]]
        
        b2 = game_state.contains_stationary_unit([26, 14])
        if b2:
            self.attackStyleHistory.append(True)
            return True
        
        stonk = [([26, 14], 1)]

        maxDist = 0
        vis = set()
        while stonk:
            pos, dist = stonk.pop()
            x, y = pos
            vis.add((x, y))
            maxDist = max(maxDist, dist)
            for i in range(4):
                nx = x+dx[i]
                ny = y+dy[i]
                b1 = game_state.game_map.in_arena_bounds([nx, ny])
                b2 = game_state.contains_stationary_unit([nx, ny])
                b3 = (nx, ny) in vis
                b4 = [nx, ny] in locations #can speed this up by using set
                if b1 and not b2 and not b3 and b4:
                    stonk.append(([nx, ny], dist+1))
        
        if maxDist >= 3: #!!
            self.attackStyleHistory.append(False)
            return False
        self.attackStyleHistory.append(True)
        return True

    def attack(self, game_state):
        # !! win if can before counter?
        # !! adapt with more bombers/demos if we dont make it through

        #game_state.attempt_spawn(WALL, [23, 11]) #block off ur current and then attack !!
        #game_state.attempt_remove([23, 11]) #block off ur current and then attack !!
        game_state.attempt_spawn(WALL, [24, 12]) #block off ur current and then attack
        game_state.attempt_remove([24, 12]) #block off ur current and then attack

        #u1 = game_state.contains_stationary_unit([26, 14])
        #u2 = game_state.contains_stationary_unit([27, 14])

        #gamelib.debug_write(self.attackStyleHistory)
        if game_state.get_resource(MP) - 5 < 5: #if we can spawn fewer than 5 scouts
            #dont do it
            return

        if self.get_cost(game_state)==5: 
            needed = 5
            game_state.attempt_spawn(INTERCEPTOR, [24, 10], needed)
        else:
            game_state.attempt_spawn(DEMOLISHER, [19, 5], 2)
            #game_state.attempt_spawn(SCOUT, [10, 3], 1) #!!
            

        #game_state.attempt_spawn(SCOUT, [9, 4], 1000) # !!
        game_state.attempt_spawn(SCOUT, [11, 2], 4)
        game_state.attempt_spawn(SCOUT, [10, 3], 1000)
    
    def finish_attack(self, game_state):
        game_state.attempt_spawn(WALL, [[26, 13]])
    
    def get_surrounding_locations(self, loc, r):
        ret = [];
        for i in range(28):
            for j in range(28):
                if (loc[0]-i)*(loc[0]-i)+ (loc[1]-j)*(loc[1]-j)<r:
                    ret.append([i, j]);
        return ret;

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units
        
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def evalFoeBomb(self, game_state, wing):
        #check if the opponent even has a funnel lined up towards the side
        #condition - if they can place 1 wall to close off, then = bomb
        dx = [0, -1, 1, 0]
        dy = [-1, 0, 0, 1] #try to move down first to increase speed
        
        if wing == 1:
            out = {(15, 13), (8, 13), (13, 13), (22, 13), (5, 13), (14, 13), (24, 13), (21, 13), (12, 13), (11, 13), (20, 13), (18, 13), (10, 13), (27, 13), (19, 13), (17, 13), (26, 13), (9, 13), (7, 13), (25, 13), (6, 13), (23, 13), (16, 13)}
            entrance = [[1, 14], [2, 14]]
        elif wing == 2:
            out = {(15, 13), (8, 13), (13, 13), (22, 13), (5, 13), (14, 13), (21, 13), (12, 13), (4, 13), (2, 13), (11, 13), (20, 13), (18, 13), (3, 13), (1, 13), (10, 13), (19, 13), (17, 13), (9, 13), (7, 13), (0, 13), (6, 13), (16, 13)}
            entrance = [[26, 14], [25, 14]]

        # if game_state.turn_number != 6 and wing != 1:
        #     return

        for start in entrance:
            vis = {(start[0], start[1], -1, -1)} 
            badplace = set()
            placeSize = {}
            #x, y, have we used the one wall, #nodes visited
            stonk = [(start[0], start[1], -1, -1, 0)]
            while stonk:
                cur = stonk.pop()
                x, y, px, py, d = cur
                # if px == 3 or px == -1:
                #     gamelib.debug_write("state", (x, y, px, py, d))
                b1 = game_state.contains_stationary_unit([x, y])
                b2 = (px, py) in badplace
                if b1 or b2:
                    continue

                nxtstate = False
                for i in range(4):
                    nx = x+dx[i]
                    ny = y+dy[i]
                    b1 = game_state.contains_stationary_unit([nx, ny])
                    b2 = not game_state.game_map.in_arena_bounds([nx, ny])
                    b3 = (ny <= 13) 
                    b4 = (nx, ny) in out
                    b5 = (nx, ny, px, py) in vis
                    b6 = (nx == px) and (ny == py)
                    if not (b1 or b2 or b3 or b4 or b5 or b6):
                        nxtstate = True
                        
                        vis.add((nx, ny, px, py))
                        stonk.append((nx, ny, px, py, d+1))

                        if px == -1 and py == -1: #try to block off
                            vis.add((x, y, nx, ny))
                            stonk.append((x, y, nx, ny, d))
                        
                    if b4:
                        nxtstate = True
                        badplace.add((px, py))
                        
                if nxtstate == False :
                    cleared = True
                    for _, __, npx, npy, ___ in stonk:
                        if npx == px and npy == py:
                            cleared = False
                            break

                    if (px, py) in placeSize:
                        placeSize[(px, py)] += d
                    else:
                        placeSize[(px, py)] = d

                    if cleared and placeSize[(px, py)] >= 10:
                        gamelib.debug_write("HAPPENED", (x, y, px, py, d))
                        return True #opponent can bomb
        
        return False

    def manageWallHistory(self, game_state):
        w1 = game_state.contains_stationary_unit([1, 14])
        w2 = game_state.contains_stationary_unit([2, 14])

        if w1:
            self.wallHistory[(1, 14)].append('E')
        else:
            self.wallHistory[(1, 14)].append('A')
        if w2:
            self.wallHistory[(2, 14)].append('E')
        else:
            self.wallHistory[(2, 14)].append('A')

        
        w3 = game_state.contains_stationary_unit([26, 14])
        w4 = game_state.contains_stationary_unit([25, 14])

        if w3:
            self.wallHistory[(26, 14)].append('E')
        else:
            self.wallHistory[(26, 14)].append('A')
        if w4:
            self.wallHistory[(25, 14)].append('E')
        else:
            self.wallHistory[(25, 14)].append('A')

    def brawlerCounter(self, game_state):
        self.analyzeCounter = [False, False]
        #[2, 14 can be deleted if theres block]
        if game_state.contains_stationary_unit([2, 14]):
            game_state.attempt_remove([2, 13])
            #game_state.attempt_spawn(WALL, [3, 13])
        else:
            game_state.attempt_spawn(WALL, [2, 13])
            game_state.attempt_upgrade([2, 13])
        
        #self.manageWallHistory(game_state)

        foeMP = game_state.get_resource(MP, 1)

        gamelib.debug_write("COUNTER EFFECTIVENESS", self.effectiveCounter)

        if foeMP <= 6:
            return

        
        verdict = self.evalFoeBomb(game_state, 1)
        #gamelib.debug_write("DFS-LEFT", verdict)
        if verdict and self.effectiveCounter[0] >= 0:
            h1 = self.wallHistory["LEFT"]
            #h2 = self.wallHistory[(2, 14)]
            if h1[-1] == 'R':
                game_state.attempt_spawn(INTERCEPTOR, [3, 10], 4 + int(foeMP//6))
                self.analyzeCounter[0] = True
                self.effectiveCounter[0] += 1
   

        verdict = self.evalFoeBomb(game_state, 2)
        #gamelib.debug_write("DFS-RIGHT", verdict)
        if verdict and self.effectiveCounter[1] >= 0:
            h3 = self.wallHistory["RIGHT"]
            if h3[-1] == 'R':
                game_state.attempt_spawn(WALL, [24, 12])
                game_state.attempt_remove([24, 12])
                game_state.attempt_spawn(INTERCEPTOR, [23, 9], 4 + int(foeMP//6))
                self.analyzeCounter[1] = True
                self.effectiveCounter[1] += 1

    def on_action_frame(self, turn_string):
        #CHANGE ON_ACTION_FRAME
        #BRAWLER
        #STARTUP
        state = json.loads(turn_string)

        leftDels = {(4, 17), (1, 14), (2, 15), (3, 16)}
        rightDels = {(26, 14), (23, 17), (24, 16), (25, 15)}

        turnInfo = state['turnInfo']
        if turnInfo[0] == 0:
            a = 1
            # self.weakTally = [0, 0, 0]
            # gamelib.debug_write("OH NO\n\n", self.effectiveBool)
            # if self.effectiveBool[0] == False:
            #     self.effectiveBool[0] = True
            #     self.effectiveCounter[0] -= 2
            # if self.effectiveBool[1] == False:
            #     self.effectiveBool[1] = True
            #     self.effectiveCounter[1] -= 2
        elif turnInfo[0] == 1 and turnInfo[2] == 0:
            p2Units = state['p2Units'][6]
            #gamelib.debug_write("UNITS", p2Units)
            a1, a2 = False, False
            for loc in p2Units:
                gamelib.debug_write("REMOVING LOC", loc)

                self.wallHistory["LEFT"].append('N')
                self.wallHistory["RIGHT"].append('N')

                dx, dy = loc[:2]
                if (dx, dy) in leftDels:
                    a1 = True
                    self.wallHistory["LEFT"].append('R')
                elif (dx, dy) in rightDels:
                    a2 = True
                    self.wallHistory["RIGHT"].append('R')
                
                if not a1:
                    self.wallHistory["LEFT"].append('N')
                if not a2:
                    self.wallHistory["RIGHT"].append('N')

            if self.analyzeCounter[0]:
                #gamelib.debug_write("SETTING FALSE", "\n\n\n")
                self.effectiveBool[0] = False
            elif self.analyzeCounter[1]:
                self.effectiveBool[1] = False

        events = state["events"]
        breaches = events["breach"]
        #deaths = events["death"]
        ataks = events["attack"]
        self_destruct = events["selfDestruct"]

        for sd in self_destruct:
            location = sd[0]
            if location[1] > 10:
                unit_owner = sd[5]
                if unit_owner == 2:
                    if location[0] <= 4:
                        self.weakWing = 1
                    else:
                        self.weakWing = 2
                    return

        for atk in ataks:
            unit_owner = atk[6]
            if unit_owner == 2:
                #gamelib.debug_write("Attack", atk, DEMOLISHER, SCOUT)
                fromLoc = atk[0]
                toLoc = atk[1] #BE BETTER HERE
                attacker = atk[3]
                if fromLoc == [24, 12]:
                    #main funnel
                    self.weakFunnel = True
                if attacker == 3 or attacker == 4:
                    if fromLoc[1] > 13:
                        if fromLoc[0] <= 4:
                            self.weakTally[0] += 1
                        else:
                            self.weakTally[1] += 1
            else:
                fromLoc = atk[0]
                if self.analyzeCounter:
                    #means we spawned interceptors
                    attacker = atk[3]
                    if attacker == 5:
                        if fromLoc[0] < 13: #Left side
                            self.effectiveBool[0] = True
                        else:
                            self.effectiveBool[1] = True

        for breach in breaches:
            location = breach[0]
            unit_owner = breach[4]
            if unit_owner == 2:
                if location[0] <= 4:
                    if self.weakTally[0] > 0:
                        self.weakWing = 1
                else:
                    if self.weakTally[1] > 0 and not self.weakFunnel:
                        self.weakWing = 2


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
