# -*- coding: utf-8 -*-
# 加载 Python Standard 和 DesignScript 库
import sys
#import clr
import math
import enum
#clr.AddReference('ProtoGeometry')
#from Autodesk.DesignScript.Geometry import *

# 该节点的输入内容将存储为 IN 变量中的一个列表。
#dataEnteringNode = IN
class PANELTYPE(enum.Enum):
    GAP = 0
    STAB = 1
    START_STAB =3
    END_STAB = 7
    MIDDLE_STAB = 15



#叠合板的拆分，总原则：需要注意过大或过小，且兼具规格尽可能统一，规格统一意味着同一标准层叠合板的规格总数小（构件厂诉求），叠合板的总数最小（起吊次数最少，减少工期，减少混凝土灌注梁和钢筋绑扎），
#设置优先级链，根据自身的要求给布局优先级评价，但各优先级中间件还是要有优先级权重，不然各家给的优先级乱给就麻烦了，譬如以工厂优先，那工厂类别的中间件的优先级应乘以10，这个权重可能也是知识产权的发力点。
#中间件机制，在给予每个layout优先级后，最终采用都布局也要能反馈给中间件，需要注册中间件，提供必要的context，触发条件，回调等，暂时以中间件名+fedback 作为结果反馈的处理函数 等
class MiddlewareController:
    #private
    _middleware_check_funs = {}
    _middleware_priority_funs ={}
    _middleware_context={}

    #public 
    def register_check_middleware(self,category,check_fun):
        if category not in self._middleware_check_funs.keys():
            self._middleware_check_funs[category]=[] 
        self._middleware_check_funs[category].append(check_fun)   

    def register_priority_middleware(self,category,priority_fun,priority_feedback_fun):
        if category not in self._middleware_priority_funs.keys():
            self._middleware_priority_funs[category]=[] 
        self._middleware_priority_funs[category].append((priority_fun,priority_feedback_fun))  

    def check_panel(self,panel):
        for key,checks in self._middleware_check_funs.items():
            for check in checks:
                rst = check(panel)
                if(rst == False): return False  #只要一个检测不过，就退出
        return True
    
    

    def get_priority_middleware_categories(self):
        return self._middleware_priority_funs.keys()

    def get_priority(self,category,layout):
        if category not in self._middleware_priority_funs.keys():
            return 0
        rst =1
        for middleware in self._middleware_priority_funs[category]:
            rst *= middleware[0](layout)

        return rst
    def update_context(self,dict):
        self._middleware_context.update(dict)
    def get_context(self,key):
        return self._middleware_context[key] if key in self._middleware_context.keys() else None
    
mc = MiddlewareController()



     

            
            

        

    

# priority_middleware_category_weight={"factory":0.5,"construction":0.5}
# priority_middleware_category = ["factory","construction"]
# def init_priority_middleware_category_weight():
#     for category in priority_middleware_category:
#         if category not in priority_middleware_category_weight.keys:
#             priority_middleware_category_weight[category]=0.5

# init_priority_middleware_category_weight()
##
def init_construction_context():
    mc.update_context({"crane.max_moment":3200*1.5})
init_construction_context()
#levels =["level1","level2"]
# #init_composed_specification = ["1000x2000"]
# priority_levels = {}
# for level in levels:
#     priority_levels[level]={}
#     priority_ = {}
#     priority_["factory"]={}
#     priority_["construction"]={}
#     for spec in init_composed_specification:
#         priority_["factory"][spec] = 0
#         priority_["construction"][spec]=0
#工厂端中间件
#priority_middleware_context["specification"]={"exist_panel_mod":{900,1200,1500,1800,}, "min_panel_width":600}
def init_factory_context():
    mc.update_context({"specification.exist_panels":{900,1200,1500,1800}})
    mc.update_context({"transportion.max_width":2500})
init_factory_context()

def factory_priority_middleware(layout):
    base_priority = 0.5
    rst_priority = base_priority

   

    exist_panel_mod = mc.get_context("specification.exist_panels")
    
    if_onepanel = True if len(layout) == 1 else False
    panel_num = 0
    for panel in layout:
        if(panel["type"] == PANELTYPE.GAP): continue #如果为gap
        panel_num += 1

    #如果是单板，优先级要高
    if if_onepanel:
        return 1
    

    # #如果所有板都符合已有模数板，优先级为1，全不符合为0
    for  i in range(len(layout)):
        if layout[i]["type"] == PANELTYPE.GAP:continue
        panel_width = layout[i]["width"]
        if panel_width in exist_panel_mod:
            rst_priority += (1-base_priority)/panel_num
            rst_priority = min(rst_priority,1)
        else:
            rst_priority -= (base_priority)/panel_num
            rst_priority = max(0,rst_priority)

    return rst_priority

def factory_priority_middleware_fedback(layout):
    #对已经选择的布局，将板的规格放入已有的规格集中
    exist_panel_mod = mc.get_context("specification.exist_panels")
    for panel in layout:
        if panel["type"] == PANELTYPE.GAP :continue
        exist_panel_mod.add(panel["width"])

#添加优先级评价中间件
mc.register_priority_middleware("factory",factory_priority_middleware,factory_priority_middleware_fedback)


def factory_check_middleware(panel):
    max_transportion_width = mc.get_context("transportion.max_width")

    delta = 0 if "delta" not in panel.keys() else panel["delta"]
    panel_type = panel["type"]
    one_panel = True if panel_type == PANELTYPE.STAB else False
    start_panel=  True if  panel_type == PANELTYPE.START_STAB  else False
    end_panel = True if   panel_type == PANELTYPE.END_STAB else False
     #交通运输尺寸控制，如果有面板的运输宽度大于车辆的最大运输宽度，则返回优先级为0
    beam_width = 200 if "beam_width" not in panel.keys() else panel["beam_width"]

    panel_width = panel["width"]
    panel_length = panel["length"]
    transportion_len = panel_width
    if one_panel:
        transportion_len += beam_width +delta    
    elif start_panel :#起始边板
        transportion_len += beam_width/2 + 300+delta
    elif end_panel:#终点板
        transportion_len += beam_width/2 + 300
    else :#中间板
        transportion_len += 300*2

    if transportion_len > max_transportion_width:
        return False
    return True

mc.register_check_middleware("factory",factory_check_middleware)
#施工阶段layoutchek
def construction_check_middleware(panel):
    #从context获取塔吊位置
    crane_position = (0,0,0)
    # if "crane" not in priority_middleware_context.keys:
     #   return True
   # max_crane_moment = priority_middleware_context["crane"]["max_moment"]
    # crane_position = priority_middleware_context["crane"]["position"]
    #临时采取最大吨位1.1吨
    max_weight = 1.5
    panel_length = panel["length"]
    panel_width = panel["width"]
    panel_base_height = 60 if "height" not in panel.keys() else  panel["height"]
  
    weight = panel_width*panel_length*panel_base_height*1/1000000000*2.5
    if weight > max_weight : return False

    return True
mc.register_check_middleware("construction",construction_check_middleware)  

#施工端优先级 中间件

def construction_priority_middleware(layout):
    base_priority = 0.5
    rst_priority = base_priority
    panel_num = len(layout)
    max_num = 10 #取值不科学，不利于后续相乘，以后要改
    rst_priority -=(1-base_priority)*panel_num/max_num
    
    #起吊次数

    #现场摆放
    return rst_priority
def construction_priority_middleware_feedback(layout):
    pass

mc.register_priority_middleware("construction",construction_priority_middleware,construction_priority_middleware_feedback)

def system_check_middleware(panel):
    panel_length = panel["length"]
    panel_width = panel["width"]
    big = max(panel_length,panel_width)
    small = min(panel_length,panel_width)
    if big/small >4 :return False
    return True

mc.register_check_middleware("system",system_check_middleware)


#原始板，轮廓过多，可简化为标准矩形板
def normalify_stab(origin_stab):
    #矩形化
    return origin_stab
#控制规格板的长宽尺寸 1. 比例 长/宽<=3 2.
#return :0 不合格
#1，合格；其他[0,1]权重
def composed_stab_check(composed_stab):#//知识产权发力点
    length = composed_stab.length
    width = composed_stab.width
    ratio_check = 3
    if(length/width <= ratio_check): return 1

#板的拆分一般按照长向进行拆分，特殊情况可以按宽度方向 1. 单块板，不分长宽  2. 分割缝不在跨中，即分格缝在距边距1/3之内 3. 满足规格板其他要求，如长宽比  
# def layout_by_width(normal_stab):
   
#     fixed_side_length = normal_stab.length
#     var_side_length =  normal_stab.width
#     layouts = do_layout(var_side_length)
#     select_layout_by_priority(layouts,fixed_side_length,)
    
#根据优先级选择合理的板的规格
#应该是有个优先级中间件链，
#根据分割，固定边长，其他已有参数，如塔吊位置，
#
# def select_layout_by_priority(layouts,fixed_side_length,others):
#     max_priority = 0
#     rst = []
#     for middleware in priority_chain:
#         for layout in layouts:
#             category = middleware.category
#             priority = middleware(layout)
#             layout.priority += priority*priority_middleware_category_weight[category]
#             if layout.priority >= max_priority:
#                 rst.append(layout)
#                 max_priority = layout.priority

#     return rst

######
# layoutcontroller   
class Layout:
    def __init__(self,common_attributes):
        self._layout = []
        self._attributes = common_attributes if common_attributes else{}
    def __getitem__(self,key):
        if isinstance(key, int):
            return self._layout[key]
        if isinstance(key,str):
            return self._attributes[key] if key in self._attributes.keys() else None
    
    def __setitem__(self,key,val):
        if isinstance(key,int):
            self._layout[key] = val
        if isinstance(key,str):
            self._attributes[key] = val

    def __len__(self):
        return self._layout.__len__()

    def __iter__(self):
        return self._layout.__iter__()
        
    def append(self,panel):
        self._layout.append(panel)
    
    def insert(self,index,panel):
        self._layout.insert(index,panel)

def default_confirm_policy(layouts):
    #最终选择长宽比接近的叠合板，
    rst_ratio = 50
    rst_layout = []
    for layout in layouts:
        ratio = 0
        for panel in layout:
            big = max(panel["width"],layout["length"])
            small = min(panel["width"],layout["length"])
            r = big/small
            if r > ratio: ratio = r
        if abs(rst_ratio-ratio)>0.001 and ratio < rst_ratio:
            rst_ratio = ratio
            rst_layout = [layout]
        elif abs(rst_ratio-ratio)<=0.001:
            rst_layout.append(layout)
    
    return rst_layout[0]


        
    

class LayoutController:
    _layout_context={}
    _confirm_funs={}
    _current_confirm_policy = None
    def __init__(self):
        self._init_layout_context()
        self._current_confirm_policy = "default"
        self._confirm_funs["default"]=default_confirm_policy
    
    def _init_layout_context(self):
        self._layout_context.update({"stab.module":100,"gab.effective_width":300})
       
   

    def update_layout_context(self,dict):
        self._layout_context.update(dict)
    def get_layout_context(self,key):
        self._layout_context[key] if key in self._layout_context.keys() else None
    def register_confirm_policy(self,name,confirm):
        self._confirm_funs.update({name,confirm})
    def change_confirm_policy(self,name):
        if name in self._confirm_funs.keys():
            self._current_confirm_policy = name



    def do_layout(self,stab):
        width = stab["width"]
        length = stab["length"]
        height = stab["height"]
        layout_common_attributes ={"length":width,"height":height,"method":"along_length"} 
        layouts_along_length = self._do_layout(length,layout_common_attributes,False)
        #按宽度方向layout
        layouts_along_width = self._do_layout(width,{"length":length,"height":height,"method":"along_width"},False)
        layouts_along_length.extend(layouts_along_width)
        layouts = layouts_along_length
        rst_layout = self._select_layout_by_priority(layouts)
        # for layout in layouts:
        #     layout["length"] = width
        #     layout["height"] =height
        # print(layouts)
        # after_checks = []
        # print(len(layouts))
        # for layout in layouts:
        #    if mc.check_panel(layout):
        #        after_checks.append(layout)
        # #print 
        # print(len(rst_layout))
        return rst_layout

    def _select_layout_by_priority(self,layouts):

        max_priority = 0
        layouts_before_priority = layouts
        layouts_ater_priority = []
        categories = mc.get_priority_middleware_categories()
        for category in categories:
            print(category,",",len(layouts_before_priority))
            max_priority = 0
            rst = []
            for layout in layouts_before_priority:
                priority = mc.get_priority(category,layout)
                if priority >max_priority:
                    rst =[]
                    max_priority = priority
                elif priority < max_priority:continue
                rst.append(layout)
            layouts_before_priority = rst
            layouts_after_priority = rst
            

        confirm_fun = self._confirm_funs[self._current_confirm_policy]
        return  confirm_fun(layouts_after_priority)

    

    def _do_layout(self,length,layout_common_attributes,enbed):
        layouts=[]
        module_number = self._layout_context["stab.module"]
        max_effective_gap = self._layout_context["gab.effective_width"]
        if length < 2*module_number + max_effective_gap:
            layout = Layout(layout_common_attributes)
            panel ={}
            panel["type"] = PANELTYPE.STAB
            panel["width"] = length
            panel["length"] = layout["length"]
            if mc.check_panel(panel):
                layout.append(panel)
                layouts.append(layout)
            return layouts
        
       

        #按一块板分
        layout = Layout(layout_common_attributes)
        panel={}
        panel["type"] = PANELTYPE.STAB if not enbed else PANELTYPE.END_STAB
        panel["width"] = length
        panel["length"] = layout["length"]

        #布局turple格式为（宽，0:板，1:gap），目前同一gap取为gap
        if mc.check_panel(panel):
            layout.append(panel)
            layouts.append(layout)

        #按有起始边板和有终止边板划分
        #其实边板从 1* module_num 开始
        mod = 0
        # start_len = mod * module_number
        # remains = length - start_len - max_effective_gap
        normal_length = length
        while True:
            mod += 1
            start_len = mod * module_number  
            start_panel ={}
            start_panel["type"] = PANELTYPE.MIDDLE_STAB
            start_panel["width"] = start_len
            start_panel["length"] = layout["length"]
            if not enbed :
                start_panel["type"] = PANELTYPE.START_STAB
                delta = length %module_number
                start_panel["delta"] = delta
                normal_length =length - delta

            remains = normal_length - start_len - max_effective_gap
            if remains < module_number :
                for layout in layouts:
                    last_panel = layout[len(layout)-1]
                    last_panel["type"] = PANELTYPE.END_STAB
                break
            
                
            if not mc.check_panel(start_panel):continue


            sub_layouts = self._do_layout(remains,layout_common_attributes,True)
            for sub_layout in sub_layouts:
                sub_layout.insert(0,start_panel)
                layouts.append(sub_layout)
                
            
        return layouts
    
        
    
lc = LayoutController()


    
    


# 将输出内容指定给 OUT 变量。
