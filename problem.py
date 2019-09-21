import networkx as nx
import pygraphviz as pg
import argparse
import json
import random
import heapq
import os
import zipfile
import re

class Node:
    id=0
    def __init__(self):
        self.state=None
        self.father=None
        self.action=None
        self.f=None
        self.cost=None
        self.depth=None
        self.h=None
        self.cut=None
        self.id=Node.id
        Node.id +=1
        self.sons=[]
        
    def keys(self):
        return (self.f,self.state,self.id)
        
    def __cmp_key(self):
        return (self.f,self.state,self.id)
           
    def __lt__(self,other):
        return self.__cmp_key()< other.__cmp_key()
    
    def path (self):
        l=[]
        n=self
        while n != None:
            n.cut="S"
            l.insert(0,n)
            n=n.father
        return l

    def all_nodes(self):
        l=[]
        stack=[self]
        while len(stack)>0:
            n = stack.pop()
            l.append(n)
            for s in n.sons:
                stack.append(s)
        return l

    def random_node(self):
        return(random.choice(self.all_nodes()))
  
    def path_json (self):
        l=self.path()
        str_path=[e.label_json() for e in l]
        return '{"path":[%s]}'%",".join(str_path)

    def label_json(self):
        str_result='\n\t{"id":%i,\n\t"state":%i,\n\t"father:"%i,\n\t"action":"%s",\n\t"f":%2.2f,\n\t"cost":%2.2f,\n\t"depth":,%i,\n\t"h":,%2.2f,\n\t"cut":"%s",\n\t"sons":[%s]}'
        father=-1 if self.father == None else self.father.id
        action=self.action if self.action != None else -1
        if len(self.sons)>0:
            sons_id=[str(s.id) for s in self.sons]
            str_sons=",".join(sons_id)
        else:
            str_sons='[]'
        str_result=str_result%(self.id,self.state,father,action,self.f,self.cost,self.depth,self.h,self.cut,str_sons)
        return str_result

    def tree_json(self,h=True):
        nodes=[]
        edges=[]
        visit=[self]
        while len(visit)>0:
            n=visit.pop()
            nodes.append(n.label_json())
            for s in n.sons:
                edges.append('\t{"nodos":[%i,%i],"cost":%i}\n'%(s.id,n.id,s.cost-n.cost))
                visit.append(s)
        nodes_str=''.join(nodes)
        edges_str=''.join(edges)
        result='{"nodes":[%s],"edges":[%s]}'%(nodes_str,edges_str)
        return result
    
    def label_dot (self,h=True):
        if h:
            label="{{%i|%2.2f}|{%i %s}|{%i|%i|%i}}"
            label = label%(self.id,self.f,self.state,"" if self.cut==None else self.cut,self.depth,self.cost,self.h)
        else:
            label="{{%i|%2.2f}|{%i %s}|{%i|%i}}"
            label= label%(self.id,self.f,self.state,"" if self.cut==None else self.cut,self.depth,self.cost)
        return "\t"+str(self.id)+"\t[shape=record,label=\"%s\"];\n"%label
        
    def tree_dot(self,h=True):
        nodes=[]
        edges=[]
        visit=[self]
        while len(visit)>0:
            n=visit.pop()
            nodes.append(n.label_dot(h))
            for s in n.sons:
                edges.append("\t%i -> %i [label=\"%i\"];\n"%(s.id,n.id,s.cost-n.cost))
                visit.append(s)
        nodes_str=''.join(nodes)
        edges_str=''.join(edges)
        result="digraph structs {\n\tnode [shape=record];\n%s\n%s\n}"%(nodes_str,edges_str)
        return result

    def tree_svg(self,file_name,h=True):
        G=pg.AGraph().from_string(string=self.tree_dot())
        G.draw(path="%s.svg"%file_name,prog='dot',format='svg')


class Problem:
    def __init__(self,name="NoName",str_json=None,nnodos=10,nconect=3,prob=0.5,cost_max=10,sol_len=4):
        self.name=name
        if not str_json==None:
            self.__from_json__(str_json)
        else: 
            self.__generate__(0,nnodos-1,nnodos,nconect,prob,cost_max,sol_len)
        pass

    def __generate__(self,orig,dest,nnodos=10,nconect=3,prob=0.5,cost_max=10,sol_len=4):
        sol_len_actual=0
        self.orig=orig
        self.dest=dest
        while sol_len_actual<sol_len:
            G=nx.to_directed(nx.barabasi_albert_graph(nnodos, nconect))
            edg_remove=[]
            for (o,d) in G.edges:
                if not (d,o) in edg_remove: # every node must have almost one egde
                    if random.random()<prob: #marked edge to remove
                        edg_remove.append((o,d))
            for (o,d) in edg_remove: #remove all edges marked
                G.remove_edge(o,d)
            for (o,d) in G.edges:
                G[o][d]['cost']=random.randint(1,cost_max)
            
            G.nodes[dest]['h']=0
            try:
                l=nx.dijkstra_path(G,orig,dest,'cost')
                cost=sum([G[l[i-1]][l[i]]['cost'] for i in range(1,len(l)) ])
                G.nodes[orig]['h']=cost #(cost,len(l),l)
                self.solution=(cost,l[:])
                sol_len_actual=len(l)
            except:
                G.nodes[orig]['h']=None
                sol_len_actual=-1
                continue

            ln1=[x for x in list(G.nodes) if x not in [orig,dest]]
            for nd in ln1:
                try:
                    l=nx.dijkstra_path(G,nd,dest,'cost')
                    cost=sum([G[l[i-1]][l[i]]['cost'] for i in range(1,len(l)) ])
                    G.nodes[nd]['h']=cost #(cost,len(l),l)
                except:
                    G.nodes[nd]['h']=None
        
        self.G=G

    def new_h(self):
        for i in self.G.nodes():
            if i==self.dest: 
                continue
            if self.G.nodes[i]['h']==None:
                self.G.nodes[i]['h']=self.G.nodes[self.orig]['h']*2
            else:
                self.G.nodes[i]['h']=random.randint(1,self.G.nodes[i]['h'])

    def to_dot(self):
        #G was adapted
        nodes_str=""
        for n in self.G.nodes():
            if self.G.nodes[n]['h']==None:
                nodes_str = nodes_str+"\t%i\t[label=\"%i\"];\n"%(n,n)
            else:
                nodes_str = nodes_str+"\t%i\t[label=\"%i:%2.1f\"];\n"%(n,n,self.G.nodes[n]['h'])
        edges_str=""
        for n in self.G.nodes():
            for e in self.G[n]:
                edges_str = edges_str + "\t%i -> %i [label=\"%i\"];\n"%(n,e,self.G[n][e]['cost'])
        return "digraph {\n %s \n %s \n}"%(nodes_str,edges_str)

    def to_svg(self,file_name,h=True):
        G=pg.AGraph().from_string(string=self.to_dot())
        s=G.draw(path="%s.svg"%file_name,prog='dot',format='svg')



    def to_json(self):
        nodes_str=[]
        for n in self.G.nodes():
            if self.G.nodes[n]['h']==None:
                nodes_str.append('\t{"id":%i}'%n)
            else:   
                nodes_str.append('\t{"id":%i,"h":%2.1f}'%(n,self.G.nodes[n]['h']))
        n_str="[\n %s]"%(",\n".join(nodes_str))
        edges_str=[]
        for n in self.G.nodes():
            for e in self.G[n]:
                edges_str.append('\t{"nodes":[%i,%i],"cost":%i}'%(n,e,self.G[n][e]['cost']))
        e_str="[\n%s]"%(",\n".join(edges_str))
        return '{"List_nodes":%s,\n"List_edges":%s}'%(n_str,e_str)
            
    def to_txt(self):
        txt="id\t[h] -> (id,cost), ... ,(id,cost)\n"
        for n in self.G.nodes():
            txt= txt + "%i\t[%2.1f]-> "%(n,self.G.nodes[n]['h'])
            for e in self.G[n]:
                txt = txt + "(%i,%i),"%(e,self.G[n][e]['cost'])
            txt=txt[:-1]+'\n'
        return txt

    def __from_json__(self,str_json):
        j=json.loads(str_json)
        self.G=nx.DiGraph()
        for n in j['List_nodes']:
            self.G.add_node(n['id'],h=n['h'])
        for e in j['List_edges']:
            self.G.add_edge(e['nodes'][0],e['nodes'][1],cost=e['cost'])
        self.orig=0
        self.dest=len(self.G.nodes())

    def search (self,strategy='A',depth=100,):
        #Set innit values
        
        #Rename h for nodes with None value
        strategies={'Breadth': lambda n:float(n.depth),
                    'Depth': lambda n:float(1.0/(float(n.depth)+1)),
                    'A': lambda n:float(n.h)+float(n.cost) if n.h != None else None,
                    'Uniform': lambda n:float(n.cost),
                    'Greedy': lambda n: float(n.h)}
        border=[]
        Node.id=0
        path=None
        act_depth=0
        memory={}
        #Set root Node
        root=Node()
        root.state=self.orig
        root.cost=0
        root.depth=0
        root.h=self.G.nodes[self.orig]['h']
        root.f=strategies[strategy](root)
        heapq.heappush(border, (root, root.keys()))
        memory[self.orig]=root.f
        #Start searchinghttps://docs.python.org/2/tutorial/datastructures.html
        while (len(border)>0) and (path == None) and (act_depth<depth):
            (n,val)=heapq.heappop(border)
            n.cut="*"
            act_depth=n.depth
            if n.state == self.dest:
                path=n.path()
            else:
                for son in dict(self.G[n.state]).keys():
                    s=Node()
                    s.state=son
                    s.father=n
                    s.depth=n.depth+1
                    s.action=str(n.state)+'->'+str(s.state)
                    s.cost=n.cost+self.G[n.state][son]['cost']
                    s.h=self.G.nodes[son]['h']
                    s.f=strategies[strategy](s)
                    n.sons.append(s)
                    #CUT
                    value_cut=s.cost if strategy=="Depth" else s.f
                    if (not s.state in memory.keys()) or memory[s.state]>value_cut:
                        memory[s.state] = value_cut
                        heapq.heappush(border, (s, s.keys()))
                    else:
                        s.cut="CUT"
        return (path,root)

def sol_files(name,strid,path,tree,stg,trace):
        if sol==None:
            print("_%s_%s no solution"%(strid,stg))
            return
        else:
            if trace>0:
                print (name+"_%s_%s"%(strid,stg))

        f=open("%s_%s_%s_"%(name,strid,stg)+'.dot','w')
        f.write(tree.tree_dot())
        f.close()
        
        tree.tree_svg("%s_%s_%s_"%(name,strid,stg))

        f=open("%s_%s_%s_"%(name,strid,stg)+'.json','w')
        f.write(tree.tree_json())
        f.close()

        f=open("%s_%s_%s_Node_"%(name,strid,stg)+'.json','w')
        f.write(tree.random_node().label_json())
        f.close()

        
        f=open("%s_%s_%s_"%(name,strid,stg)+'.json','w')
        f.write(path[-1].path_json())
        f.close()

def create_zip(namefile):
    path=re.compile('%s*'%namefile)
    listfiles=list(filter(path.match,os.listdir('.')))
    fzip=zipfile.ZipFile(namefile+'.zip',mode='a')
    for fl in listfiles:
        filename, file_extension = os.path.splitext(fl)
        if not(file_extension == '.zip'):
            fzip.write(fl)
            os.remove(fl)
    fzip.close()


if __name__ == "__main__":

    
    parser = argparse.ArgumentParser()
    parser.add_argument("-n","--name", default='Noname',help="Problem name")
    parser.add_argument("-nd","--nnodes",default='15',type=int,help="Number of nodes of graph")
    parser.add_argument("-c","--nconect",default='3',type=int,help="Number of conctions from a node to others")
    parser.add_argument("-p","--prob",default=0.6,type=int,help="Remove probability for edges in biderectional graph")
    parser.add_argument("-l","--lensol",default='6',type=int,help="Minimal length for path solution")
    parser.add_argument("-w","--worst",default='2',type=int,help="Number of worst problems")
    parser.add_argument("-s","--strategy",default='ABDUG',type=str,help="Char list of:(A),(B)readth,(D)epth,(U)niform and (G)reedy")
    parser.add_argument("-d","--depth",default='0',type=int,help="Max depth ")
    parser.add_argument("-t","--trace",default='0',type=int,help="[0|1] active trace")
    args = parser.parse_args()
    

    p=Problem(name=args.name,nnodos=args.nnodes+1,nconect=args.nconect,prob=args.prob,sol_len=args.lensol)
    f=open(p.name+'.json','w')
    f.write(p.to_json())
    f.close()

    f=open(p.name+'.dot','w')
    f.write(p.to_dot())
    f.close()

    p.to_svg(p.name+'')


    #A star solution
    (sol,tree)=p.search(strategy='A')
    if args.depth==0:
        depth=len(sol)+3
    else:
        depth=args.depth

    if 'A' in args.strategy:
        sol_files(p.name,'',sol,tree,'A',args.trace)

    list_stg=[('B','Breadth'),('D','Depth'),('U','Uniform'),('G','Greedy')]
    for stg in list_stg:
        if stg[0] in args.strategy:
            (sol,tree)=p.search(strategy=stg[1],depth=depth)
            sol_files(p.name,'',sol,tree,stg[1],args.trace)

    create_zip(p.name)

    while args.worst>0:
        p.new_h()
        f=open(p.name+'_h%i.json'%args.worst,'w')
        f.write(p.to_json())
        f.close()

        f=open(p.name+'_h%i.dot'%args.worst,'w')
        f.write(p.to_dot())
        f.close()

        p.to_svg(p.name+'_h%i.dot'%args.worst)
        

        #A star solution
        (sol,tree)=p.search(strategy='A')
        if args.depth==0:
            depth=len(sol)+3
        else:
            depth=args.depth

        if 'A' in args.strategy:
            sol_files(p.name,'h%i'%args.worst,sol,tree,'A',args.trace)

        list_stg=[('B','Breadth'),('D','Depth'),('U','Uniform'),('G','Greedy')]
        for stg in list_stg:
            if stg[0] in args.strategy:
                (sol,tree)=p.search(strategy=stg[1],depth=depth)
                sol_files(p.name,'h%i'%args.worst,sol,tree,stg[1],args.trace)
        
        create_zip(p.name+'_h%i'%args.worst)

        args.worst = args.worst - 1

        