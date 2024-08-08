#ßee https://www.geeksforgeeks.org/python-lambda-anonymous-functions-filter-map-reduce/?ref=ml_lbp

def sum(a,b): #https://www.youtube.com/shorts/ss-I6WAiMFA
    return a+b
sum_lambda=(lambda a,b:a+b)#(1,2)
# c=sum_lambda(1,2)


def main():
    Max = lambda a, b : a if(a > b) else b
    print( Max(17, 42))

    List = [[2,3,4],[1, 4, 16, 64],[3, 6, 9, 12]]
    sortList = lambda x: (sorted(i) for i in x)
    secondLargest = lambda x, f : [y[len(y)-2] for y in f(x)]
    res = secondLargest(List, sortList)
    print(res)

    li = [5, 7, 22, 97, 54, 62, 77, 23, 73, 61]
    final_list = list(filter(lambda x: (x % 2 != 0), li))
    print(final_list)

    ages = [13, 90, 17, 59, 21, 60, 5]
    adults = list(filter(lambda age: age > 18, ages))
    print(adults)

if __name__ == '__main__':
    main()
