from gsp2 import GSP
import random

if __name__ == '__main__':
    slot_clicks = [1,2,3]
    reserve = 20
    bids = [
        (i,random.randint(5, 47))
        for i in range(10)
    ]
    print(bids)
    print(GSP.compute(slot_clicks, reserve, bids))