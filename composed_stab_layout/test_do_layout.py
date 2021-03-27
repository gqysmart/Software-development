import sys
sys.path.append(".")
import composed_stab_layout.layout_suggest as layout_suggest

stab ={}
stab["width"] = 6050
stab["length"] = 3000
stab["height"] = 60

layout = layout_suggest.lc.do_layout(stab)
rst =""
for panel in layout:
    rst += str(panel["width"])+"|"

rst +="("+layout["method"]+")"
print(rst)




