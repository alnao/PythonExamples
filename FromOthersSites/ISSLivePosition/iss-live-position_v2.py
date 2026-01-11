import requests
import plotly.express as px

#see http://open-notify.org/

# from https://www.facebook.com/story.php?story_fbid=1343778957776319&id=100064326836270&post_id=100064326836270_1343778957776319&rdid=yLFlxzqN5sTwH04l#


# use open-notify.org API to get current ISS position
url =" http://api.open-notify.org/iss-now.json"
response = requests.get(url)
data = response.json()

# extract latitude and longitude
latitude = float(data['iss_position']['latitude'])
longitude = float(data['iss_position']['longitude'])
# create a scatter geo plot to visualize the ISS position
fig = px.scatter_geo(lat=[latitude], lon=[longitude],
                        title="Current Position of the ISS")
# add red marker for ISS position
fig.update_traces(marker=dict(size=10, color="red", symbol="circle"))
# customize map appearance
fig.update_geos(showland=True, landcolor="LightGreen",
                showocean=True, oceancolor="LightBlue",
                showcountries=True, countrycolor="Gray")
# adjust layout for better visualization
fig.update_layout(height=600, margin={"r":0,"t":30,"l":0,"b":0})
# move the center of the map to the ISS position
fig.update_geos(center=dict(lat=latitude, lon=longitude))
# display the map
fig.show()

