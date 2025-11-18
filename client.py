from baresipy import BareSIP
from time import sleep

to = "11111"

gateway = "172.20.2.210:7776"
user = "7003"
pswd = "7003"

b = BareSIP(user, pswd, gateway, debug=True)

#b.call(to)

# while b.running:
#     sleep(0.5)
#     if b.call_established:
#         b.hang()
#         b.quit()
