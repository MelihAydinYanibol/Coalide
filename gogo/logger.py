"""
This files only job is to log.
"""

import sys

def lg(a="",b="",c="",d="",e="",f="",g="",h="",i="",j="",k="",l="",m="",n="",o="",p="",q="",r="",s="",t="",u="",v="",w="",x="",y="",z=""):
    global DEBUG
    DEBUG = False
    if len(sys.argv)>1:
        if sys.argv[1]=="-debug":
            DEBUG = True
            print(a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z)

    return DEBUG