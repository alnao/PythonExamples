
#see https://www.youtube.com/watch?v=xV0B1Y0tem0
#Code With me Using Python to Build an Expense Tracker App

class Expense:
    def __init__(self,date,description,money):
        self.date=date
        self.description=description
        self.money=money

class Manager:
    def __init__(self):
        self.list=[]
    def add(self, expense):
        self.list.append(expense)
    def remove(self,index):
        if 0 <= index <len(self.list):
            del self.list[index]
        else:
            print("Invalid index ")
    def view(self):
        if len(self.list)==0:
            print ("No expense found")
        else:
            print ("List:")
            for i,exp in enumerate(self.list, start=1):
                print ( f"{i} Date:{exp.date}, Desc:{exp.description}, Money:{exp.money}" )
    def total(self):
        total=sum(expense.money for expense in self.list)
        print ( f"Total expense is ${total:.2f}")

def main():
    manager = Manager()
    while True:
        print("Expense manager")
        print("1 to view")
        print("2 to total")
        print("3 to add")
        print("4 to remove")
        print("5 to exit")
        choise = input ("Select operation (1-5): ")
        if choise=="3":
            date = input("Enter date (YYYY-MM-DD): ")
            description = input ("Enter description: ")
            money = float(input ("Enter value: "))
            exp=Expense(date,description,money)
            manager.add(exp)
        elif choise=="4":
            index = input ("Enter index to remove (zero to skip): ")
            if index!="0":
                manager.remove(int(index)-1)
        elif choise=="1":
            manager.view()
        elif choise=="2":
            manager.total()
        elif choise=="5":
            break
        else:
            print("Invalid command")
    print ("Bye bye")
            


if __name__ == "__main__":
    main()
