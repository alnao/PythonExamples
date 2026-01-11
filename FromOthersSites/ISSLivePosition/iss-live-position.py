import requests
import plotly.express as px
# use wheretheiss.at API to get current ISS position
#fetch current ISS position data from the API
url="https://api.wheretheiss.at/v1/satellites/25544"
response=requests.get(url)
data=response.json()
#extract latitude and longitude
latitude=data['latitude']
longitude=data['longitude']
#create a scatter geo plot to visualize the ISS position
fig = px.scatter_geo(lat=[latitude], lon=[longitude],
                        projection="orthographic",
                        title="Current Position of the ISS")
#add red marker for ISS position
fig.update_traces(marker=dict(size=10, color="red", symbol="circle"))
#customize map appearance
fig.update_geos(showland=True, landcolor="LightGreen",
                showocean=True, oceancolor="LightBlue",
                showcountries=True, countrycolor="Gray")
#adjust layout for better visualization
fig.update_layout(height=600, margin={"r":0,"t":30,"l":0,"b":0})
# move the center of the map to the ISS position
fig.update_geos(center=dict(lat=latitude, lon=longitude))
#display the map
fig.show()  