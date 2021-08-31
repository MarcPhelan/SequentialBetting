function sideUpdate(s1,s2) {
            if(s1 == "heads"){
                document.getElementById('AutoSideBet').value="tails";
                var x = document.getElementById("AutoSideBet");
                var option = document.createElement("option");
                option.text = "Tails";
                x.add(option,0);
            } else if(s1 == "tails"){
                document.getElementById('AutoSideBet').value="heads";
                var x = document.getElementById("AutoSideBet");
                var option = document.createElement("option");
                option.text = "Heads";
                x.add(option,0);
            }
         
        }

function betUpdate(bet){
        
    //    var bet = +document.getElementById(bet); // + coerces its operand into a number
        var current_wealth = {{current_wealth_flask}};
        
        var auto_bet = current_wealth - bet;
        

        document.getElementById("AutoAmountBet").value = auto_bet;
        }


// function to ensure only number keys are pressed

function isNumberKey(evt){
    var charCode = (evt.which) ? evt.which : event.keyCode
    if (charCode > 31 && (charCode != 46 &&(charCode < 48 || charCode > 57)))
            return false;
    return true;
     }
//function to automatically update the amount bet
function percentageUpdate(bet){
    var auto_percentage = 100 - bet;
    document.getElementById("AutoAmountBet").value = auto_bet;
}


