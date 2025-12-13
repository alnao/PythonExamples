# see https://www.youtube.com/watch?v=3tyaO-OE0K0
import time
from datetime import datetime, timedelta
def time_dec(base_fn): # see https://www.youtube.com/watch?v=3tyaO-OE0K0
  def enchanted_fn(*args,**kargs): #**kargs means any/some parameters with keywords (example tea_type="green")
    start_time=time.time()
    result = base_fn(*args,**kargs)
    end_time=time.time()
    delta_time = end_time - start_time
    print (f"Task time {delta_time} seconds ")
    print ("-------------------")
    return result
  return enchanted_fn
@time_dec #mode1
def braw_tea():
  print("Brewing tea...")
  time.sleep(2)
  print("Tea is ready")
braw_tea();     
# braw_tea=time_dec(braw_tea); # mode2 separete decorator and function code!
braw_tea()

@time_dec  
def make_matcha():
  print("Making matcha")
  time.sleep(5)
  print("Matcha is ready")
  return f"Drink mucha by {datetime.now()-timedelta(minutes=30)}"
make_matcha()

@time_dec  
def braw_tea_with_type(tea_type,quantity):
  print(f"Brewing {tea_type} {quantity} tea..")
  time.sleep(2 * quantity)
  print("Tea is ready")
braw_tea_with_type(tea_type="green",quantity=2)