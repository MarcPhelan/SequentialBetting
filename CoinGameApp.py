
from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from sqlalchemy.dialects.postgresql import JSON
import random
import numpy as np
import pandas as pd
import sys
import json
from random import choices
import os
from flask_migrate import Migrate
import psycopg2
from flask_admin.contrib.sqla import ModelView
from flask_admin import Admin
import time


##################################################################################
                            ##### Set up App & Database ####
##################################################################################

#initiate app
app = Flask(__name__)
app.secret_key = os.environ['SECRET_KEY'] #environmental variable
#app.config["SECRET_KEY"] = "youwillneverguess"


#create & configure database
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://mphelan:"+os.environ['DB_PASS']+"@localhost/coin_store"
#app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:11223344@localhost/coin_store"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
Migrate(app , db)
admin = Admin(app)


#create table in database
class Results(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    PlayerID = db.Column(db.String(100), nullable=False, unique=True, default=0) #user id
    GameID = db.Column(db.Integer, unique=True, default = 0) #random generated id for duration of game
    Employment = db.Column(db.String(50), nullable=False, default = 0) #employment status
    Education = db.Column(db.String(50), nullable=False, default = 0) #education level
    Wealth = db.Column(db.String(50), nullable=False, default = 0) #current wealth band
    Wage = db.Column(db.String(50), nullable=False, default = 0) #current wage band
    Condition = db.Column(db.Integer, nullable=False, default = 0) #percent or absolute
    FirstGame = db.Column(db.Integer, nullable=False, default = 0) # full or partial first
    Bankrupt = db.Column(db.Integer, nullable=False, default = 0)#whether player went bankrupt or not
    GameData = db.Column(JSON) #save game data as json


admin.add_view(ModelView(Results, db.session))

##################################################################################
                    ##### Set up required lists,arrays & flask variables #####
##################################################################################

#create lits/arrays needed
GameID_array = []
Round_array = []
Wealth_array =[]
Bet_array = []
Side_array = []
Result_array = []
Outcome_array = []


#flask variables to appear on the rules pages ###
#whether playing full or partial game
partial_bet_flask = 'In order to place a bet, you must enter an amount and pick a side (heads or tails).'
fulla_bet_flask = 'During this game you are required to bet all of your capital during each round. However, you are free to split your capital across the two sides (heads or tails) in whatever proportion you like. The computer is programmed to accept bets to the closest 10p.'
fullp_bet_flask = 'During this game you are required to bet all of your capital during each round. However, you are free to split your capital across the two sides (heads or tails) in whatever proportion you like.'
#game_bet_flask = #either of the above

#whether playing a full/patrial percentage or absolute game
pa_bet_flask = 'The amount you can bet must be between £1 and your current capital. In other words, the smallest bet you can make is £1 and the largest bet you can make is ‘All-in’. You are free to place bets to the nearest 10p.'
pp_bet_flask = 'We ask you to please express your bet as a percentage of your current capital. This percentage can be between 1% and 100%. In other words, the smallest bet you can make is 1% of your current capital and the largest bet you can make is an ‘All-in’ 100%. You are free to place bets to the nearest 0.1%.'
fa_bet_flask = 'For example, say your current capital is £100 and you bet £55 on heads. As you must bet all of your £100, the computer is programmed to automatically bet the remaining £45 on tails.'
fa_bet_flask1 = 'Therefore, your final bet would be £55 on heads and £45 on tails. Please be sure that you are happy with both sides of the bet before submitting it. Once the final bet has been submitted you cannot alter it.'
fp_bet_flask = 'We ask you to please express your bet as a percentage of your current capital. The computer is programmed to accept bets to the closest 0.1%'
fp_bet_flask1 = 'For example, say your current capital is £100 and you bet 55% on heads. As you must bet 100%, the computer is programmed to automatically bet the remaining 45% on tails. '
fp_bet_flask2 = 'Therefore, your final bet would be 55% of your current capital on heads and 45% of your current capital on tails. Please be sure that you are happy with both sides of the bet before submitting it. Once the final bet has been submitted you cannot alter it.'
#rules_bet_flask = #one of the above

#describe the calculation used for winnings
partial_cal_flask = 'As you are betting on a coin flip, only two outcomes are possible. Either the coin lands heads or it lands tails. If you correctly predict the side that appears, we will double your bet and add it to your capital. However, if your prediction is wrong you lose your bet. In other words, we subtract your bet from your capital.'
full_cal_flask = 'As you are betting on a coin flip, only two outcomes are possible. Either the coin lands heads or it lands tails. Whatever side of the coin appears we will double the amount you bet on that "winning" side. However, at the same time you will lose the amount you bet on the "losing" side that did not appear.'
#cal_flask = #either of the above

#examples of the calculations
pa_exp_flask1 = 'Say your current capital is £100 and you place a £55 bet on heads. If the coin lands heads we would return £110 to you (your original bet of £55 plus £55 for your winnings). Because this £110 includes your original £55 bet you should note that your net profit for the round would be £55. This means your new capital would be £155.'
pa_exp_flask2 = 'However, if the coin lands tails, you would lose your £55 bet, and your new capital would be £45 (£100-£55).'
pp_exp_flask1 = 'Say your current capital is £100 and you place a 55% bet on heads. This is equivalent to betting £55 on heads. Therefore, if the coin lands heads we would return £110 to you (your original bet of £55 plus £55 for your winnings). Because this £110 includes your original £55 bet you should note that your net profit for the round would be £55. This means your new capital would be £155. '
pp_exp_flask2 = 'However, if the coin lands tails, you would lose your 55% bet, and your new capital would be £45 (£100 - £55).'
fa_exp_flask1 = 'Say your current capital is £100 and you place the following bet: £55 on heads and £45 on tails. If a heads appears we would return £65 to you (your original bet of £55 plus £55 for your winnings, minus the £45 you bet on tails). Because this £65 includes your origianl £55 bet, your net profit for the round would be £10 (£65-£55) and your new wealth would be £110.'
fa_exp_flask2 = 'However, if the coin lands tails your final net outcome would be different. We would double the £45 you bet on tails so it becomes £90, and then subtract the £55 you bet on heads. This means we would return £35 (£90-£55) to you. You should note that your original bet was £45, but the money you got back was only £35. This means you lost £10 for the round (£45-£35) and your new wealth would be £90.'
fp_exp_flask1 = 'Say your current capital is £100 and you place the following bet: 55% of your capital on heads and 45% on tails. This is equivalent to betting £55 on heads and £45 on tails. '
fp_exp_flask2 = 'If a heads appears we would return £65 to you (your original bet of 55% of £100, plus your winnings of £55, minus the 45% of £100 you bet on tails). Because this £65 includes your original £55 bet (55% of £100), your net profit for the round would be £10 (£65-£55) and your new wealth would be £110.'
fp_exp_flask3 = 'However, if the coin lands tails your final net outcome would be different. We would double the 45% of £100 (£45) you bet on tails so it becomes £90, and then subtract the 55% of £100 (£55) you bet on heads. This means we would return £35 (£90-£55) to you. You should note that your original bet was 45% of £100 (£45), but the money you got back was only £35. This means you lost £10 for the round (£45-£35) and your new wealth would be £90.'
#exp_flask =  #one of the others
#exp_full_flask = #one or fa_exp_flask2 or fp_exp_flask2

#(only for full game) = import to notice how wealth, bet on heads & bet on tails affect winnings
full_notice_flask = 'Therefore, it is important to note that your potential winnings depend on the amount you bet on heads and the amount you bet on tails.'



##################################################################################
                    ##### Set up required functions #####
##################################################################################

#function that imitates a coin flip (1=heads with probability .6 and 2=tails with probability .4)
def flip():
    np.random.seed(1407) #Reproducability
    heads_probability = .6
    tails_probability = 1- heads_probability
    value  = [1,2]
    prob = [heads_probability , tails_probability]
    R = choices(value , prob)
    outcome = int(R[-1])
    return(outcome)


#create function to save players game data as json and insert into database
def save_data():
    #create dictionary
    result={}

    #Add arrays/lists to the dictionary
    result["GameID"] = GameID_array
    result["Round"] = Round_array
    result["Wealth"] = Wealth_array
    result["Bet"] = Bet_array
    result["Side"] = Side_array
    result["Outcome"] = Outcome_array
    result["Result"] = Result_array

    for data in result:
        print(data)

    data = json.dumps(result, indent=4)
    #print(data)
    GameID = session['GameID']
    player = Results.query.filter_by(GameID=GameID).first()
    player.GameData = data
    db.session.commit()



##################################################################################
                        ##### Opening pages of app ####
##################################################################################

def GameIdGenerate():
    GameID = random.randrange(1,10000) #create & assign random game id to player
    session['GameID'] = GameID


@app.route('/', methods=["GET","POST"])
def welcome():
    if request.method == "POST":
        PlayerID = request.form['ID']
        GameIdGenerate()
        GameID = session['GameID']
        exists = Results.query.filter_by(PlayerID = PlayerID).first()
        if not exists:
            insert = Results(GameID=GameID , PlayerID = PlayerID)
            try:
                db.session.add(insert)
                db.session.commit()
                #print('GameID and PlayerID posted and saved to db', GameID)
                return redirect("/Consent")
            except:

                return redirect("/")
        else:
            pass
    return render_template("Index.html",title_flask="Welcome")


#POST players ID & append into an array, set up session value, & Render Consent_Page
@app.route('/Consent', methods=['GET', 'POST'])
def consent():
    return render_template("Consent.html",title_flask='Consent')


@app.route('/Submit', methods=['GET', 'POST'])
def submit():
    GameID = session['GameID']
    if request.method == 'POST':
        consent = request.form['consent'] #retrieve input from the html form
        if consent == 'yes':
            return render_template('Demographics1.html',
            title_flask = 'Demographics') #If consent="yes" then continue to rules
        else:
            return render_template('NoConsent.html') #If consent="no" then then redirect to end
    else:
        print('Problem with submit function and posting consent')


@app.route('/Demographics2', methods=['GET', 'POST'])
def demographics2():
    GameID = session['GameID']
    if request.method == 'POST':
        Education = request.form['education']
        Employment = request.form['employment']
        player = Results.query.filter_by(GameID=GameID).first()
        player.Education = Education
        player.Employment = Employment
        db.session.commit()
        #print('Education & Employment posted and saved to db')
        return render_template('Demographics2.html',
            title_flask = 'Demographics')
    else:
        print('Problem with demographics2 function')


@app.route('/Background', methods=['GET', 'POST'])
def background():
    GameID = session['GameID']
    if request.method == 'POST':
        Wage = request.form['wage']
        Wealth = request.form['wealth']
        player = Results.query.filter_by(GameID=GameID).first()
        player.Wage = Wage
        player.Wealth = Wealth
        db.session.commit()
        #print('Wage & Wealth posted and saved to db')
        return render_template('Background.html')


##################################################################################
    #### hidden routes/functions that control how player moves through the task ####
##################################################################################

#route that controls a players journey through the games
@app.route('/Random/', methods=['GET', 'POST'])
def branch():
    GameID = session['GameID']
    pp_counter = 0
    pa_counter = 0
    fa_counter = 0
    fp_counter = 0
    session['pp_counter'] = pp_counter
    session['fp_counter'] = fp_counter
    session['pa_counter'] = pa_counter
    session['fa_counter'] = fa_counter

    condition = np.random.choice(a = [1, 2], p = [0.5, 0.5])
    firstgame = np.random.choice(a = [1, 2], p = [0.5, 0.5])
    player = Results.query.filter_by(GameID=GameID).first()
    player.Condition=int(condition)
    player.FirstGame=int(firstgame)
    db.session.commit()
    #print('Players condition (1=plays percentage game, 2=plays absolute game) is', condition)
    #print('Players first game (1=plays partial first, 2=plays full first) is', firstgame)

    if condition == 1 and firstgame == 1: #plays partial percentage first
        pp_counter += 1
        session['pp_counter'] = pp_counter
        return render_template('Rules.html',
            game_bet_flask = partial_bet_flask,
            rules_bet_flask = pp_bet_flask,
            cal_flask = partial_cal_flask,
            exp_flask = pp_exp_flask1,
            exp_flask2 = pp_exp_flask2,
            title_flask = 'Partial Percentage Betting Game')
    elif condition == 1 and firstgame == 2: #plays full percentage first
        fp_counter += 1
        session['fp_counter'] = fp_counter
        return render_template('Rules.html',
            game_bet_flask = fullp_bet_flask,
            rules_bet_flask = fp_bet_flask,
            rules_bet_flask1 = fp_bet_flask1,
            rules_bet_flask2 = fp_bet_flask2,
            cal_flask = full_cal_flask,
            exp_flask = fp_exp_flask1,
            exp_flask1 = fp_exp_flask2,
            exp_flask2 = fp_exp_flask3,
            full_notice_flask = full_notice_flask,
            title = 'Full Percentage Betting Game')
    elif condition == 2 and firstgame == 1: #plays partial absolute first
        pa_counter += 1
        session['pa_counter'] = pa_counter
        return render_template('Rules.html',
            game_bet_flask = partial_bet_flask,
            rules_bet_flask = pa_bet_flask,
            cal_flask = partial_cal_flask,
            exp_flask = pa_exp_flask1,
            exp_flask1 = pa_exp_flask2,
            title = 'Partial Absolute Betting Game')
    else: #plays full absolute first
        fa_counter += 1
        session['fa_counter'] = fa_counter
        return render_template('Rules.html',
            game_bet_flask = fulla_bet_flask,
            rules_bet_flask = fa_bet_flask,
            rules_bet_flask1 = fa_bet_flask1,
            cal_flask = full_cal_flask,
            exp_flask = fa_exp_flask1,
            exp_flask1 = fa_exp_flask2,
            full_notice_flask = full_notice_flask,
            title = 'Full Absolute Betting Game')




@app.route('/Balance', methods=['GET', 'POST'])
def counterbalance():
    pp_counter = session['pp_counter']
    fp_counter = session['fp_counter']
    pa_counter = session['pa_counter']
    fa_counter = session['fa_counter']

    if pp_counter == 1: #pp_counter==1 means play has played partial percentage game. Next plays full percentage game.
        pp_counter += 1
        session['pp_counter'] = pp_counter
        return render_template('Rules.html',
            game_bet_flask = fullp_bet_flask,
            rules_bet_flask = fp_bet_flask,
            rules_bet_flask1 = fp_bet_flask1,
            rules_bet_flask2 = fp_bet_flask2,
            cal_flask = full_cal_flask,
            exp_flask = fp_exp_flask1,
            exp_flask1 = fp_exp_flask2,
            exp_flask2 = fp_exp_flask3,
            full_notice_flask = full_notice_flask,
            title = 'Full Percentage Betting Game') #render next game that they havent played
    elif fp_counter == 1: #fp_counter==1 means play has played full percentage game. Next plays partial percent game.
        fp_counter += 1
        session['fp_counter'] = fp_counter
        return render_template('Rules.html',
            game_bet_flask = partial_bet_flask,
            rules_bet_flask = pp_bet_flask,
            cal_flask = partial_cal_flask,
            exp_flask = pp_exp_flask1,
            exp_flask2 = pp_exp_flask2,
            title_flask = 'Partial Percentage Betting Game') #render next game that they havent played
    elif pa_counter ==1: #pa_counter==1 means play has played partial absolute game. Next plays full absolute game.
        pa_counter += 1
        session['pa_counter'] = pa_counter
        return render_template('Rules.html',
            game_bet_flask = fulla_bet_flask,
            rules_bet_flask = fa_bet_flask,
            rules_bet_flask1 = fa_bet_flask1,
            cal_flask = full_cal_flask,
            exp_flask = fa_exp_flask1,
            exp_flask1 = fa_exp_flask2,
            full_notice_flask = full_notice_flask,
            title = 'Full Absolute Betting Game') #render next game that they havent played
    elif fa_counter == 1: #fa_counter==1 means play has played full absolute game. Next plays partial absolute game.
        fa_counter += 1
        session['fa_counter'] = fa_counter
        return render_template('Rules.html',
            game_bet_flask = partial_bet_flask,
            rules_bet_flask = pa_bet_flask,
            cal_flask = partial_cal_flask,
            exp_flask = pa_exp_flask1,
            exp_flask1 = pa_exp_flask2,
            title = 'Partial Absolute Betting Game') #render next game that they havent played
    else:
        return render_template('End.html') #if counters==2 the player has played both games. Render the endpage.


#route that controls which game template renders
@app.route('/Game', methods=['GET', 'POST'])
def game():
    pp_counter = session['pp_counter']
    pa_counter = session['pa_counter']
    fp_counter = session['fp_counter']
    fa_counter = session['fa_counter']
    if pp_counter == 1 or pa_counter == 1 or fp_counter == 2 or fa_counter == 2:
         return redirect(url_for('partial_game'))
    elif fp_counter == 1 or fa_counter == 1 or pp_counter == 2 or pa_counter == 2:
        return redirect(url_for('full_game'))
    else:
        print('Problem moving from rules to game')


##################################################################################
                         ##### App game pages ####
##################################################################################


                        ############ Full Game  ############


# Set up main full game page
@app.route("/FullGame/", methods=['GET'])
def full_game():
    #passing values
    GameID = session["GameID"]
    pp_counter = session['pp_counter']
    fp_counter = session['fp_counter']
    pa_counter = session['pa_counter']
    fa_counter = session['fa_counter']

    #Initial parameters & counters
    heads_counter = 0
    tails_counter = 0
    start_wealth = 20
    current_wealth = start_wealth
    total_trials = 5
    trial = 1
    multiplier = 2
    session["heads_counter"] = heads_counter
    session["tails_counter"] = tails_counter
    session["current_wealth"] = current_wealth
    session["trial"] = trial
    session["multiplier"] = multiplier

    #create instance of an outcome (either heads or tails)
    outcome = int(flip())
    session["outcome"] = outcome

    #used on the html page
    trial_flask = str(trial)
    current_wealth_flask = str(current_wealth)
    heads_counter_flask = str(heads_counter)
    tails_counter_flask = str(tails_counter)

    if fp_counter == 1 or pp_counter == 2:
        return render_template('FullPercentageGame.html',
            trial_flask = trial_flask,
            current_wealth_flask = current_wealth_flask,
            heads_counter_flask =heads_counter_flask,
            tails_counter_flask = tails_counter_flask)
    elif fa_counter == 1 or pa_counter == 2:
        return render_template('FullAbsoluteGame.html',
            trial_flask = trial_flask,
            current_wealth_flask = current_wealth_flask,
            heads_counter_flask =heads_counter_flask,
            tails_counter_flask = tails_counter_flask)
    else:
        print('Problem with full game function')




@app.route("/FullGame", methods=['POST'])
def next_full_game():
    total_trials = 5
    GameID = session["GameID"]
    pp_counter = session['pp_counter']
    fp_counter = session['fp_counter']
    pa_counter = session['pa_counter']
    fa_counter = session['fa_counter']
    heads_counter = session["heads_counter"]
    tails_counter = session["tails_counter"]
    current_wealth = session["current_wealth"]
    trial = session["trial"]
    outcome = session["outcome"]
    multiplier = session["multiplier"]
    #print("Previous outcome was " , outcome)
    result=""
    fraction_bet = 0
    message = ""

    if fp_counter == 1 or pp_counter == 2:
        amount_bet = request.form.get('amount_bet') #player entered amount
        amount_bet1 = request.form.get('AutoAmountBet') #automatically updated field
        amount_bet = float(amount_bet)
        amount_bet1 = float(amount_bet1)
        fraction_bet = amount_bet/100  #turn into fraction
        fraction_bet1 = 1-fraction_bet
        side_bet = request.form.get('side_bet') #player entered side
        side_bet1 = request.form.get('AutoSideBet') #automatically updated field

        if amount_bet > 100:
            message = "You do not have that much money. Please try again."
            color_code = 'red'
        elif outcome == 1 and (side_bet =="heads"):
            heads_counter += 1
            bet = current_wealth * fraction_bet #get absolute amount bet
            opp_bet = current_wealth - bet #find other side of the bet
            result = (multiplier * bet) #double amount bet
            net_result = result - (bet + opp_bet) #net result
            abs_net = round(abs(net_result), 1) #absolute net gain/loss (for flask html variables) round to 2 decimal places
            current_wealth = current_wealth + net_result
            current_wealth = round(abs(current_wealth), 1)
            if net_result > 0:
                message = f"The coin landed HEADS. You won £{abs_net} this round and your new wealth is £{current_wealth}." #f-string to display monetary amount won
                color_code = 'green'
            else:
                message = f"The coin landed HEADS. You lost £{abs_net} this round and your new wealth is £{current_wealth}." #f-string to display monetary amount won
                color_code = 'red'
        elif outcome == 2 and (side_bet =="heads"):
            tails_counter += 1
            bet = current_wealth * fraction_bet1
            opp_bet = current_wealth - bet
            result = (multiplier * bet)
            net_result = result - (bet + opp_bet) #net outcome for round
            abs_net = round(abs(net_result), 1)
            current_wealth = current_wealth + net_result
            current_wealth = round(abs(current_wealth), 1)
            if net_result > 0:
                message = f"The coin landed TAILS. You won £{abs_net} this round and your new wealth is £{current_wealth}."
                color_code = 'green'
            else:
                message = f"The coin landed TAILS. You lost £{abs_net} this round and your new wealth is £{current_wealth}."
                color_code = 'red'
        elif outcome == 1 and (side_bet =="tails"):
            heads_counter += 1
            bet = current_wealth * fraction_bet1
            opp_bet = current_wealth - bet
            result = (multiplier * bet)
            net_result = result - (bet + opp_bet)
            abs_net = round(abs(net_result), 1)
            current_wealth = current_wealth + net_result
            current_wealth = round(abs(current_wealth), 1)
            if net_result > 0:
                message = f"The coin landed HEADS. You won £{abs_net} this round and your new wealth is £{current_wealth}." #f-string to display monetary amount won
                color_code = 'green'
            else:
                message = f"The coin landed HEADS. You lost £{abs_net} this round and your new wealth is £{current_wealth}." #f-string to display monetary amount won
                color_code = 'red'
        else:
            tails_counter += 1
            bet = current_wealth * fraction_bet #get absolute amount bet
            opp_bet = current_wealth - bet #find other side of the bet
            result = (multiplier * bet) #double amount bet
            net_result = result - (bet + opp_bet) #net result
            abs_net = round(abs(net_result), 1)
            current_wealth = current_wealth + net_result
            current_wealth = round(abs(current_wealth), 1)
            if net_result > 0:
                message = f"The coin landed TAILS. You won £{abs_net} this round and your new wealth is £{current_wealth}."
                color_code = 'green'
            else:
                message = f"The coin landed TAILS. You lost £{abs_net} this round and your new wealth is £{current_wealth}."
                color_code = 'red'


    elif fa_counter == 1 or pa_counter == 2:
        amount_bet = request.form['amount_bet'] #player entered amount
        amount_bet1 =request.form['AutoAmountBet'] #automatically updated field
        amount_bet = float(amount_bet)
        amount_bet1 = float(amount_bet1)
        amount_bet = round(float(amount_bet), 1)
        amount_bet1 = round(float(amount_bet1), 1)
        side_bet = request.form.get('side_bet') #player entered side
        side_bet1 = request.form.get('AutoSideBet') #automatically updated field

        if amount_bet > current_wealth:
            message = "You do not have that much money. Please try again."
            color_code = 'red'
        elif outcome == 1 and (side_bet =="heads"):
            heads_counter += 1
            result = (multiplier * amount_bet) #amount_bet = on heads & amount_bet1 = on tails
            net_result = result - (amount_bet + amount_bet1) #net result for the round
            abs_net = round(abs(net_result), 1) #absolute net gain/loss (for flask html variables) round to 2 decimal places
            current_wealth = round(current_wealth + net_result, 1)
            if net_result > 0:
                message = f"The coin landed HEADS. You won £{abs_net} this round and your new wealth is £{current_wealth}."
                color_code = 'green'
            else:
                message = f"The coin landed HEADS. You lost £{abs_net} this round and your new wealth is £{current_wealth}."
                color_code = 'red'
        elif outcome == 2 and (side_bet =="heads"):
            tails_counter += 1
            result = (multiplier * amount_bet1) #amount_bet = on heads & amount_bet1 = on tails
            net_result = result - (amount_bet1+amount_bet) #net gain for round
            abs_net = round(abs(net_result), 1)
            current_wealth = round(current_wealth + net_result, 1)
            if net_result > 0:
                message = f"The coin landed TAILS. You won £{abs_net} this round and your new wealth is £{current_wealth}."
                color_code = 'green'
            else:
                message = f"The coin landed TAILS. You lost £{abs_net} this round and your new wealth is £{current_wealth}."
                color_code = 'red'
        elif outcome == 1 and (side_bet =="tails"):
            heads_counter += 1
            result = (multiplier * amount_bet1) #amount_bet = on tails & amount_bet1 = on heads
            net_result = result - (amount_bet1 + amount_bet)
            abs_net = round(abs(net_result), 1)
            current_wealth = round(current_wealth + net_result, 1)
            if net_result > 0:
                message = f"The coin landed HEADS. You won £{abs_net} this round and your new wealth is £{current_wealth}."
                color_code = 'green'
            else:
                message = f"The coin landed HEADS. You lost £{abs_net} this round and your new wealth is £{current_wealth}."
                color_code = 'red'
        else:
            tails_counter += 1
            result = (multiplier * amount_bet) #amount_bet = on tails & amount_bet1 = on heads
            net_result = result - (amount_bet+amount_bet1)
            abs_net = round(abs(net_result), 1)
            current_wealth = round(current_wealth + net_result, 1)
            if net_result > 0:
                message = f"The coin landed TAILS. You won £{abs_net} this round and your new wealth is £{current_wealth}."
                color_code = 'green'
            else:
                message = f"The coin landed TAILS. You lost £{abs_net} this round and your new wealth is £{current_wealth}."
                color_code = 'red'
    else:
        print('Problem with next full game function (error in "if counters ==" block')

    #Append arrays for the round
    if result:
        GameID_array.append(GameID)
        Round_array.append(trial)
        Wealth_array.append(current_wealth)
        Bet_array.append(fraction_bet)
        if side_bet == "t":
            Side_array.append("Tail")
        else:
            Side_array.append("Head")
        if outcome == 1:
            Outcome_array.append("Head")
        else:
            Outcome_array.append("Tail")
        Result_array.append(net_result)

        #start new round
        trial = trial + 1
        #print('Results appeneded into arrays successfully')
    else:
        print('Problem with next full game function (error in "if result:" block)')


         #new outcome
    outcome = int(flip())

    #Passing ID session values
    session["GameID"] = GameID
    session["heads_counter"] = heads_counter
    session["tails_counter"] = tails_counter
    session["current_wealth"] = current_wealth
    session["trial"] = trial
    session["outcome"] = outcome
    session["multiplier"] = multiplier

    if trial > total_trials:
        current_wealth = session["current_wealth"]
        current_wealth_flask = current_wealth
        GameID = session['GameID']
        save_data()
        bankrupt = 0
        player = Results.query.filter_by(GameID=GameID).first()
        player.Bankrupt = bankrupt
        db.session.commit()
        #print('Game completed and data saved to db')
        time.sleep(.75)
        return render_template('GameOver.html', current_wealth_flask = current_wealth_flask)
    elif current_wealth < 1:
        GameID = session['GameID']
        save_data()
        player = Results.query.filter_by(GameID=GameID).first()
        player.Bankrupt = trial
        db.session.commit()
        #print('Player went bankrupt and data saved to db')
        return render_template('Bankrupt.html')
    else:
        print('Problem with next full game function (error when trying to end game)')

    trial_flask = str(trial)
    current_wealth_flask = str(current_wealth)
    heads_counter_flask = str(heads_counter)
    tails_counter_flask = str(tails_counter)
    message_flask = str(message)


    if fp_counter == 1 or pp_counter == 2:
        return render_template('FullPercentageGame.html',
            trial_flask = trial_flask,
            current_wealth_flask = current_wealth_flask,
            heads_counter_flask =heads_counter_flask,
            tails_counter_flask = tails_counter_flask,
            color_code = color_code,
            message_flask = message_flask)
    elif fa_counter == 1 or pa_counter == 2:
        return render_template('FullAbsoluteGame.html',
            trial_flask = trial_flask,
            current_wealth_flask = current_wealth_flask,
            heads_counter_flask =heads_counter_flask,
            tails_counter_flask = tails_counter_flask,
            color_code = color_code,
            message_flask = message_flask)
    else:
        print('Problem with next full game function (error rendering templates)')



                    ############ Partial Game  ############



# Set up main partial game page
@app.route('/PartialGame', methods=['GET'])
def partial_game():
    GameID = session["GameID"]
    pp_counter = session['pp_counter']
    fp_counter = session['fp_counter']
    pa_counter = session['pa_counter']
    fa_counter = session['fa_counter']

    #Initial parameters & counters
    heads_counter = 0
    tails_counter = 0
    start_wealth = 20
    current_wealth = start_wealth
    total_trials = 5
    trial = 1
    multiplier = 2
    session["heads_counter"] = heads_counter
    session["tails_counter"] = tails_counter
    session["current_wealth"] = current_wealth
    session["trial"] = trial
    session["multiplier"] = multiplier

    #create instance of an outcome (either heads or tails)
    outcome = int(flip())
    session["outcome"] = outcome

    #used on the html page
    trial_flask = str(trial)
    current_wealth_flask = str(current_wealth)
    heads_counter_flask = str(heads_counter)
    tails_counter_flask = str(tails_counter)

    #print(pp_counter, " and ", fp_counter)
    if pp_counter == 1 or fp_counter == 2:
        return render_template('PartialPercentageGame.html',
        trial_flask = trial_flask,
        current_wealth_flask = current_wealth_flask,
        heads_counter_flask = heads_counter_flask,
        tails_counter_flask = tails_counter_flask)
    elif pa_counter == 1 or fa_counter ==2:
        return render_template('PartialAbsoluteGame.html',
        trial_flask = trial_flask,
        current_wealth_flask = current_wealth_flask,
        heads_counter_flask = heads_counter_flask,
        tails_counter_flask = tails_counter_flask)
    else:
        print('Problem with partial game function')






@app.route('/PartialGame', methods=['POST'])
def next_partial_game():
    total_trials = 5
    GameID = session["GameID"]
    pp_counter = session['pp_counter']
    fp_counter = session['fp_counter']
    pa_counter = session['pa_counter']
    fa_counter = session['fa_counter']
    heads_counter = session["heads_counter"]
    tails_counter = session["tails_counter"]
    current_wealth = session["current_wealth"]
    trial = session["trial"]
    outcome = session["outcome"]
    multiplier = session["multiplier"]
    result = ""

    if pp_counter == 1 or fp_counter == 2:
        amount_bet = request.form.get('amount_bet')
        side_bet = request.form.get('side_bet')
        amount_bet = round(float(amount_bet), 2) #between 1 and 100
        fraction_bet = amount_bet/100 #turn into fraction

        if amount_bet > 100:
            message = "You do not have that much money. Please try again."
            color_code = 'red'
        elif amount_bet < 1:
            message = "Bet must be greater than 1%. Please try again."
            color_code = 'red'
        else:
            if outcome == 1 and (side_bet =="h"): #win
                heads_counter += 1
                bet = (fraction_bet * current_wealth)
                result = (multiplier * bet)
                net_result = round((result - bet), 1)
                current_wealth = round((current_wealth + net_result), 1)
                message = f"The coin landed HEADS. You won £{net_result} this round and your new wealth is £{current_wealth}." #f-string to display monetary amount won
                color_code = 'green'
            elif outcome == 2 and (side_bet =="h"): #lost
                tails_counter += 1
                bet = (fraction_bet * current_wealth)
                result = round((bet), 1)
                current_wealth = round((current_wealth - result), 1)
                message = f"The coin landed TAILS. You lost £{result} this round and your new wealth is £{current_wealth}."
                color_code = 'red'
            elif outcome == 1 and (side_bet =="t"): #lost
                heads_counter += 1
                bet = (fraction_bet * current_wealth)
                result = round((bet), 1)
                current_wealth = round((current_wealth - result), 1)
                message = f"The coin landed HEADS. You lost £{result} this round and your new wealth is £{current_wealth}."
                color_code = 'red'
            else: #win
                tails_counter += 1
                bet = (fraction_bet * current_wealth)
                result = (multiplier * bet)
                net_result = round((result - bet), 1)
                current_wealth = round((current_wealth + net_result), 1)
                message = f"The coin landed TAILS. You won £{net_result} this round and your new wealth is £{current_wealth}."
                color_code = 'green'
    #pa_counter == 1 --> play partial absolute game first
    #fa_counter == 2 --> played full absolute game now render partial game
    elif pa_counter == 1 or fa_counter ==2:
        amount_bet = request.form.get('amount_bet')
        side_bet = request.form.get('side_bet')

        if float(amount_bet) > current_wealth:
            message = "You do not have that much money. Please try again."
            color_code = 'red'
        elif float(amount_bet) < 1:
            message = "You cannot bet below £1. Please try again."
            color_code = 'red'
        else:
            amount_bet = round(float(amount_bet), 1)
            if outcome == 1 and (side_bet =="h"): #win
                heads_counter += 1
                result = (multiplier * amount_bet)
                net_result = round(result - amount_bet, 1) #net gain
                current_wealth = round(current_wealth + net_result, 1)
                message = f"The coin landed HEADS. You won £{net_result} this round and your new wealth is £{current_wealth}." #f-string to display monetary amount won
                color_code = 'green'
            elif outcome == 2 and (side_bet =="h"): #lost
                tails_counter += 1
                result = round(amount_bet, 1)
                current_wealth = round(current_wealth - result, 1)
                message = f"The coin landed TAILS. You lost £{result} this round and your new wealth is £{current_wealth}."
                color_code = 'red'
            elif outcome == 1 and (side_bet =="t"): #lost
                heads_counter += 1
                result = round(amount_bet, 1)
                current_wealth = round(current_wealth - result, 1)
                message = f"The coin landed HEADS. You lost £{result} this round and your new wealth is £{current_wealth}."
                color_code = 'red'
            else: #win
                tails_counter += 1
                result = (multiplier * amount_bet)
                net_result = round(result - amount_bet, 1) #net gain
                current_wealth = round(current_wealth + net_result, 1)
                message = f"The coin landed TAILS. You won £{net_result} this round and your new wealth is £{current_wealth}."
                color_code = 'green'
    else:
        print('Problem with next partial game function (error in "if counters ==" block')

    if result:
        try:
            GameID_array.append(GameID)
            try:
                Round_array.append(trial)
            except:
                pass
            try:
                Wealth_array.append(current_wealth)
            except:
                pass
            try:
                Bet_array.append(fraction_bet)
            except:
                pass
            try:
                if side_bet == "t":
                    Side_array.append("Tail")
                else:
                    Side_array.append("Head")
            except:
                pass

            try:
                if outcome == 1:
                    Outcome_array.append("Head")
                else:
                    Outcome_array.append("Tail")
            except:
                pass

            try:
                Result_array.append(net_result)
            except:
                pass

            #start new round
            trial = trial + 1
            #print('Results appeneded into arrays successfully')
        except Exception as e:
            print('Problem with next partial game function (error in "if result:" block)', e)

    #new outcome
    outcome = int(flip())

    session["GameID"] = GameID
    session["heads_counter"] = heads_counter
    session["tails_counter"] = tails_counter
    session["current_wealth"] = current_wealth
    session["trial"] = trial
    session["outcome"] = outcome
    session["multiplier"] = multiplier

    #If the game has gone through all the trials or a players becomes bankrupt, redirect player to next game or to 'End.html' page
    if trial > total_trials:
        GameID = session['GameID']
        current_wealth = session["current_wealth"]
        current_wealth_flask = current_wealth
        save_data()
        bankrupt = 0 # 0= player did not go bankrupt
        player = Results.query.filter_by(GameID=GameID).first()
        player.Bankrupt = bankrupt
        db.session.commit()
        #print('Game completed and data saved to db')
        time.sleep(.75)
        return render_template('GameOver.html', current_wealth_flask = current_wealth_flask)
    elif current_wealth < 1:
        GameID = session['GameID']
        save_data()
        player = Results.query.filter_by(GameID=GameID).first()
        player.Bankrupt = trial
        db.session.commit()
        #print('Player went bankrupt and data saved to db')
        return render_template('Bankrupt.html')
    else:
        print('Problem with next partial game function (error when trying to end game)')

    #for html
    trial_flask = str(trial)
    current_wealth_flask = str(current_wealth)
    heads_counter_flask = str(heads_counter)
    tails_counter_flask = str(tails_counter)
    message_flask = str(message)

    #pp_counter == 1 --> play partial percentage game first
    #fp_counter == 2 --> played full percentage game now play partial game
    if pp_counter == 1 or fp_counter == 2:
        return render_template('PartialPercentageGame.html',
            trial_flask = trial_flask,
            current_wealth_flask = current_wealth_flask,
            heads_counter_flask =heads_counter_flask,
            tails_counter_flask = tails_counter_flask,
            color_code = color_code,
            message_flask = message_flask)
    #pa_counter == 1 --> play partial absolute game first
    #fa_counter == 2 --> played full absolute game now render partial game
    elif pa_counter == 1 or fa_counter ==2:
        return render_template('PartialAbsoluteGame.html',
            trial_flask = trial_flask,
            current_wealth_flask = current_wealth_flask,
            heads_counter_flask =heads_counter_flask,
            tails_counter_flask = tails_counter_flask,
            color_code = color_code,
            message_flask = message_flask)
    else:
        print('Problem with next partial game function (error rendering templates)')



#if player goes bankrupt
@app.route('/GameOver', methods=['GET'])
def game_over():
    render_template('GameOver.html',
        title_flask = 'Game Over')


#end (consent=no)
@app.route('/End', methods=['GET'])
def end():
    render_template('End.html')

#redirect participants back to Prolific
@app.route('/Prolific', methods=['GET'])
def prolific():
    return redirect("https://www.prolific.co/")


if __name__ == "__main__":
    app.run(debug = True)

