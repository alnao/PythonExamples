from tkinter import *
import tkinter as tk
from  tkinter import ttk

class ConsoleEc2sg:
    def __init__(self,frame,profilo,configuration,classe_sdk,list_to_clipboard):
        for widget in frame.winfo_children():
            widget.destroy()
        self.configuration=configuration
        self.profilo=profilo
        self.frame=frame
        self.classe_sdk=classe_sdk
        self.list_to_clipboard=list_to_clipboard
        self.lista_o1=[]
        self.load_frame()
        self.reload_method=self.load_frame
        
    def load_frame(self):
        for widget in self.frame.winfo_children():
            widget.destroy()
        service=self.classe_sdk(self.profilo)
        self.list=service.get_list()
        self.detail=service.describe_security_group
        self.add_permission=service.add_permission
        #NOOO self.revoke_all_permission=service.revoke_all_permission
        self.crea_window()



    def crea_window(self):
        self.frame.columnconfigure(2)
        self.frame1 = ttk.Frame(self.frame, width=550, height=630)
        self.frame1.grid(row = 1, column = 2, sticky = tk.W, padx = 2) 
        self.frame1.pack(side=LEFT, expand = 1)
        self.frame2 = ttk.Frame(self.frame, width=650, height=630)
        self.frame2.grid(row = 1, column = 2, sticky = tk.E, padx = 2) 
        self.frame2.pack(side=LEFT, expand = 1)
        self.scroll = Scrollbar(self.frame1)
        self.scroll.pack(side=RIGHT, fill=Y)
        self.tree = ttk.Treeview(self.frame1,yscrollcommand=self.scroll.set,height=50)
        self.tree['columns'] = ( 'Id', 'GroupName', 'Description')
        self.tree.column("#0", width=0,  stretch=NO)
        self.tree.column("Id",anchor=CENTER,width=150)
        self.tree.column("GroupName",width=150)
        self.tree.column("Description",width=150)
        self.tree.heading("#0",text="",anchor=CENTER)
        self.tree.heading("Id",text="GroupId",anchor=CENTER)
        self.tree.heading("GroupName",text="GroupName",anchor=CENTER)
        self.tree.heading("Description",text="Description",anchor=CENTER)
        i=1
        for gruppo in self.list:
            self.tree.insert(parent='',index='end',iid=i,text='',
                values=(gruppo['GroupId'],gruppo['GroupName'], gruppo['Description']))
            i=i+1
        self.tree.bind("<Double-1>", self.open_detail)
        self.tree.bind("<Button-3>", func = lambda event :self.list_to_clipboard(self.tree,0) )
        self.tree.pack(side=LEFT, expand = 1)
        self.free2_loaded=False
        #return tab

    def open_detail(self, event): #(frame,profilo,lista_istanze,istanza):
        item = self.tree.selection()[0]
        id_gruppo = self.tree.item(item)['values'][0]
        gruppo={}
        nome=''
        for e in self.list:
            if id_gruppo==e['GroupId']:
                gruppo=e
                nome= gruppo['GroupName']
        self.gruppo=gruppo
        if self.free2_loaded==True:
            self.frame2.pack_forget()# or frm.grid_forget() depending on whether the frame was packed or grided. #self.frame2.Destroy()
            self.frame2 = ttk.Frame(self.frame)
        
        l=Label(self.frame2, text="Gruppo: " + id_gruppo + " "  )
        l.bind("<Button-1>", func = lambda event :self.list_to_clipboard(self.tree,0) )
        l.pack()
        l2=Label(self.frame2, text="Nome: " + nome )
        l2.bind("<Button-1>", func = lambda event :self.list_to_clipboard(self.tree,0) )
        l2.pack()
        self.frame2a = ttk.Frame(self.frame2,height=300)
        self.scroll2 = Scrollbar(self.frame2a)
        self.scroll2.pack(side=RIGHT, fill=Y)
        self.free2_loaded=True
        self.tree2 = ttk.Treeview(self.frame2a,yscrollcommand=self.scroll2.set,height=10)
        self.tree2['columns'] = ('Chiave', 'Valore')
        self.tree2.column("#0", width=0,  stretch=NO)
        self.tree2.column("Chiave", width=200)
        self.tree2.column("Valore",anchor=CENTER,width=480)
        self.tree2.heading("#0",text="",anchor=CENTER)
        self.tree2.heading("Chiave",text="Chiave",anchor=CENTER)
        self.tree2.heading("Valore",text="Valore",anchor=CENTER)
        i=0
        for key in gruppo:
            self.tree2.insert(parent='',index='end',iid=i,text='',
                    values=(key,gruppo[key]) )
            i=i+1
        self.tree2.bind("<Button-3>", func = lambda event :self.list_to_clipboard(self.tree2,1) )
        self.tree2.pack()
        self.frame2b = ttk.Frame(self.frame2)
#TODO inserire regola 
        l_name= Label(self.frame2b, text="Permissions " + nome )
        #l_name.pack()
        l_name.bind("<Button-1>", lambda e:self.open_window_set_tag())

        self.scroll2b = Scrollbar(self.frame2b)
        self.scroll2b.pack(side=RIGHT, fill=Y)
        self.tree3 = ttk.Treeview(self.frame2b,yscrollcommand=self.scroll2b.set,height=15)
        self.tree3['columns'] = ('FromPort', 'ToPort','CidrIp','Desc')
        self.tree3.column("#0", width=0,  stretch=NO)
        self.tree3.column("FromPort",anchor=CENTER, width=100)
        self.tree3.column("ToPort",anchor=CENTER,width=100)
        self.tree3.column("CidrIp",width=200)
        self.tree3.column("Desc",width=200)
        self.tree3.heading("#0",text="",anchor=CENTER)
        self.tree3.heading("FromPort",text="FromPort",anchor=CENTER)
        self.tree3.heading("ToPort",text="ToPort",anchor=CENTER)
        self.tree3.heading("CidrIp",text="CidrIp",anchor=CENTER)
        self.tree3.heading("Desc",text="Desc",anchor=CENTER)
        i=0
        for row in gruppo['IpPermissions']:
            for e in row['IpRanges']:
                desc=""
                if 'Description' in e:
                    desc=e['Description']
                self.tree3.insert(parent='',index='end',iid=i,text='',
                    values=(row['FromPort'],row['ToPort'],row['IpProtocol'] + " " + e['CidrIp'], desc ) )
                i=i+1
        #self.tree3.bind("<Double-1>", self.open_detail_tag)
        self.tree3.bind("<Button-3>", func = lambda event :self.list_to_clipboard(self.tree3,1) )
        self.tree3.pack()
        self.frame2a.pack()    
        self.frame2b.pack()            
        self.frame2.pack(side=LEFT)
"""
{'Description': 'AWS created security group for d-93676fd512 directory controllers', 'GroupName': 'd-93676fd512_controllers',
'IpPermissions': [{'FromPort': 138, 'IpProtocol': 'udp', 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Custom UDP rule'}],
'Ipv6Ranges': [], 'PrefixListIds': [], 'ToPort': 138, 'UserIdGroupPairs': []}, {'FromPort': 445, 'IpProtocol': 'udp', 'IpRanges': 
[{'CidrIp': '0.0.0.0/0', 'Description': 'Custom UDP rule'}], 
'Ipv6Ranges': [], 'PrefixListIds': [], 'ToPort': 445, 'UserIdGroupPairs': []}, {'FromPort': 464, 'IpProtocol': 'udp', 'IpRanges': 
[{'CidrIp': '0.0.0.0/0', 'Description': 'Custom UDP rule'}], 'Ipv6Ranges': [], 'PrefixListIds': [], 'ToPort': 464, 'UserIdGroupPairs':
 []}, {'FromPort': 464, 'IpProtocol': 'tcp', 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Custom TCP rule'}], 'Ipv6Ranges': [], 
 'PrefixListIds': [], 'ToPort': 464, 'UserIdGroupPairs': []}, {'FromPort': 389, 'IpProtocol': 'udp', 'IpRanges': [{'CidrIp': '0.0.0.0/0', 
 'Description': 'Custom UDP rule'}], 'Ipv6Ranges': [], 'PrefixListIds': [], 'ToPort': 389, 'UserIdGroupPairs': []}, 
 {'FromPort': 53, 'IpProtocol': 'udp', 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Default DNS UDP rule'}], 'Ipv6Ranges': [], 
 'PrefixListIds': [], 'ToPort': 53, 'UserIdGroupPairs': []}, {'FromPort': 389, 'IpProtocol': 'tcp', 'IpRanges': [{'CidrIp': '0.0.0.0/0', 
 'Description': 'Default LDAP rule'}], 'Ipv6Ranges': [], 'PrefixListIds': [], 'ToPort': 389, 'UserIdGroupPairs': []}, 
 {'FromPort': -1, 'IpProtocol': 'icmp', 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Default ICMP rule'}], 'Ipv6Ranges': [], 'PrefixListIds': [], 
'ToPort': -1, 'UserIdGroupPairs': []}, {'FromPort': 445, 'IpProtocol': 'tcp', 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 
'Default SMB rule'}], 'Ipv6Ranges': [], 'PrefixListIds': [], 'ToPort': 445, 'UserIdGroupPairs': []}, 
{'FromPort': 123, 'IpProtocol': 'udp', 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Custom UDP rule'}], 'Ipv6Ranges': [], 
'PrefixListIds': [], 'ToPort': 123, 'UserIdGroupPairs': []}, {'FromPort': 88, 'IpProtocol': 'tcp', 'IpRanges': [{'CidrIp': '0.0.0.0/0', 
'Description': 'Custom TCP rule'}], 'Ipv6Ranges': [], 'PrefixListIds': [], 'ToPort': 88, 'UserIdGroupPairs': []}, {'FromPort': 3268, '
IpProtocol': 'tcp', 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Custom TCP rule'}], 'Ipv6Ranges': [], 'PrefixListIds': [], 
'ToPort': 3269, 'UserIdGroupPairs': []}, {'FromPort': 1024, 'IpProtocol': 'tcp', 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 
'Custom TCP rule'}], 'Ipv6Ranges': [], 'PrefixListIds': [], 'ToPort': 65535, 'UserIdGroupPairs': []}, {'IpProtocol': '-1', 'IpRanges'
: [], 'Ipv6Ranges': [], 'PrefixListIds': [], 'UserIdGroupPairs': [{'Description': 'Allow All traffic from SG', 'GroupId': 'sg-0a31f889186305019', 
'UserId': '740456629644'}]}, {'FromPort': 135, 'IpProtocol': 'tcp', 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Custom TCP rule'}], 
'Ipv6Ranges': [], 'PrefixListIds': [], 'ToPort': 135, 'UserIdGroupPairs': []}, {'FromPort': 636, 'IpProtocol': 'tcp', 'IpRanges': [{'CidrIp':
 '0.0.0.0/0', 'Description': 'Custom TCP rule'}], 'Ipv6Ranges': [], 'PrefixListIds': [], 'ToPort': 636, 'UserIdGroupPairs': []}, 
 {'FromPort': 53, 'IpProtocol': 'tcp', 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Default DNS TCP rule'}], 'Ipv6Ranges': [],
   'PrefixListIds': [], 'ToPort': 53, 'UserIdGroupPairs': []}, {'FromPort': 88, 'IpProtocol': 'udp', 'IpRanges': [{'CidrIp': '0.0.0.0/0',
     'Description': 'Custom UDP rule'}], 'Ipv6Ranges': [], 'PrefixListIds': [], 'ToPort': 88, 'UserIdGroupPairs': []}], 'OwnerId': 
     '740456629644', 'GroupId': 'sg-0a31f889186305019', 'IpPermissionsEgress': [{'IpProtocol': '-1', 'IpRanges': [], 'Ipv6Ranges': [],
       'PrefixListIds': [], 'UserIdGroupPairs': [{'Description': 'Allow All traffic from SG', 'GroupId': 'sg-0a31f889186305019', 'UserId'
       : '740456629644'}]}], 'VpcId': 'vpc-0720cb9155edcbce9'}
       
"""