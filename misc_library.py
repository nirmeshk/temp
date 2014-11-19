from __future__ import division
def xtile(lst,lo=0,hi=100,width=50,
             chops=[0.1 ,0.3,0.5,0.7,0.9],
             marks=["-" ," "," ","-"," "],
             bar="|",star="*",show=" %3.0f"):
    """The function _xtile_ takes a list of (possibly)
    unsorted numbers and presents them as a horizontal
    xtile chart (in ascii format). The default is a 
    contracted _quintile_ that shows the 
    10,30,50,70,90 breaks in the data (but this can be 
    changed- see the optional flags of the function).
    """
    def pos(p)   : return ordered[int(len(lst)*p)]
    def place(x) : 
        return int(width*float((x - lo))/(hi - lo))
    def pretty(lst) : 
        return ', '.join([show % x for x in lst])
    ordered = sorted(lst)
    lo      = min(lo,ordered[0])
    hi      = max(hi,ordered[-1])
    what    = [pos(p)   for p in chops]
    where   = [place(n) for n in  what]
    out     = [" "] * width
    for one,two in zip(where,where[1:]):
        for i in range(one,two): 
          out[i] = marks[0]
        marks = marks[1:]
    out[int(width/2)]    = bar
    out[place(pos(0.5))] = star 
    return ''.join(out) +  "," +  pretty(what)