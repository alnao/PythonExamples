import pandas as pd
#see https://medium.com/codex/run-a-python-code-on-aws-batch-part-1-creation-of-python-script-and-docker-container-1b01dc89eaed

# initialize list of lists
data = [['Alberto', 1984], ['Andrea', 1977], ['Pietro', 1948]]

# Create the pandas DataFrame
df = pd.DataFrame(data, columns=['Name', 'Date'])

if __name__ == '__main__':
    print("-"*50)
    print(df)
    print("-"*50)