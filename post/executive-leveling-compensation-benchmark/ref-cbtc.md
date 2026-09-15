# Align CTBC to UOB where UOB and rest fixed, move CTBC only 
11 職等 · 資深經理 · UOB VP1
12 職等 · 資深經理（主管職） · UOB VP2
13 職等 · 協理（部室主管） · UOB FVP
14 職等 · 協理（部室主管） · UOB SVP
15 職等 · 資深協理 / 副總經理 · UOB ED
16 職等 · 資深副總 / 執行副總 · UOB MD


still not align, as now we should all using one global coordinator, you should just copy the height corrdinator from CTBC to aling 

# ALign Fubon to CTBC where CTBC and rest not moved, only Fubon moved
ref of Fubon mapping to CTBC
Fubon 6 should align CTBC 13 from start to end 
Fubon 5 should align CTBC 12 
Fubon 3 should cover CTBC 8 and 9


all in global coordinator 
so just align the height in stack chart

still not align, as now we should all using one global coordinator, you should just copy the height corrdinator from CTBC to aling 

# POtentail BUGs happen many times that always dont have dependecy on coordinator.
I found the problem: Fubon’s spans are defined against CTBC, but the special boundary-copy logic only runs when CTBC is primary. With UOB primary, Fubon falls back to its own centers, so Fubon 6 drifts away from UOB FVP/CTBC 13. I’ll add equivalent UOB mappings for Fubon 3/5/6 and use the UOB primary boundaries too.


# still with bug that 
do not using UOB as primary, using global invarient as primary wil change time by time. 
nonw if i have primary as singpaore civil service, it is not aling again







3:45 AM






Working for 19s







You’re right—the renderer was still recalculating non-primary lane centers from the selected company. I’ll make every lane’s geometry use its canonical global level directly, and set Fubon’s CTBC-referenced centers to the corresponding CTBC global levels. This removes primary-axis drift, including when Singapore Civil Service is primary.



double check on all company, stack are all using canonical global levels ,  no spand, hight dependecy on each other 

each of the company vertical stack should not have gap vertically.


very wrong... the previous version is better as 
each of the company vertical stack should not have gap vertically.
please revert to previous one, when remove the depenece, we keep the original number first.