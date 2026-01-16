#import the package and bring the content
import stockpyl
# bringing WW module from the stockpyl package and importing 
from stockpyl.wagner_whitin import wagner_whitin


nbPeriods=int(input("Enter the number of periods: "))
holdingCost=float(input("Enter the holding cost: "))
fixedCost=float(input("Enter the fixed ordering cost: "))
user_input = input("Enter demand per period separated by spaces: ")
demand= list(map(float, user_input.split()))

Q,cost,carriedCost,nextOrder=wagner_whitin(nbPeriods,holdingCost,fixedCost,demand)
print("Quantities ordered in each period: ",Q)
print("The cost of inventory policy is: ",cost)
print("Cost carried to the next period: ", carriedCost)
print("The list of next order period: ", nextOrder)
