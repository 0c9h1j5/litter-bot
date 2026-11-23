"""깊이 렌더로 바닥 위 돌출물 찾기 (logs/2026-11-23_depth_protrusion.md)"""
import sys, time, mujoco, numpy as np
from PIL import Image
m = mujoco.MjModel.from_xml_path(sys.argv[1]); d = mujoco.MjData(m); mujoco.mj_forward(m, d)
W,H=640,480
r = mujoco.Renderer(m, H, W)
# 머리 카메라 대역: 높이 1.3 m(가정), 코트 쪽(-y)에서 벤치 쪽(+y)을 내려다봄
cam = mujoco.MjvCamera(); cam.type=mujoco.mjtCamera.mjCAMERA_FREE
cam.lookat[:] = [0.4, 0.9, 0.0]; cam.distance = 1.9; cam.azimuth = 90; cam.elevation = -42
t=time.time(); r.update_scene(d, cam); rgb = r.render()
r.enable_depth_rendering(); r.update_scene(d, cam); depth = r.render(); r.disable_depth_rendering()
print(f"render rgb+depth {1000*(time.time()-t):.0f} ms, depth range {depth.min():.2f}~{depth.max():.2f} m")
# 깊이 → 월드 좌표
fovy=np.deg2rad(m.vis.global_.fovy); f=0.5*H/np.tan(fovy/2)
az,el=np.deg2rad(cam.azimuth),np.deg2rad(cam.elevation)
fwd=np.array([np.cos(el)*np.cos(az),np.cos(el)*np.sin(az),np.sin(el)])
pos=np.array(cam.lookat)-cam.distance*fwd
right=np.cross(fwd,[0,0,1]); right/=np.linalg.norm(right); up=np.cross(right,fwd)
u,v=np.meshgrid(np.arange(W),np.arange(H))
x=(u-W/2+0.5)/f; y=-(v-H/2+0.5)/f
dirs=fwd[None,None,:]+x[...,None]*right+y[...,None]*up
pts=pos+depth[...,None]*dirs   # depth = 카메라 축 방향 거리
z=pts[...,2]
# 바닥 위 돌출(3~30 cm), 벽·벤치 영역(y>0.88)은 높이 기준만
mask=(z>0.03)&(pts[...,1]<1.45)&(depth<5)
from scipy import ndimage
lab,n=ndimage.label(mask)
objs=[]
for i in range(1,n+1):
    sel=lab==i
    if sel.sum()<30: continue
    c=pts[sel].mean(0); top=float(z[sel].max()); objs.append(('litter?' if top<0.30 else 'obstacle', round(c[0],2),round(c[1],2),round(top,2),int(sel.sum())))
print("floor protrusions (x,y,top z,px):"); [print(" ",o) for o in objs]
print("truth litter:", [(m.body(i).name, np.round(d.xpos[i][:2],2).tolist()) for i in range(m.nbody) if m.body(i).name.startswith("litter") and d.xpos[i][2]<0.3])
vis=(np.clip(depth,0,4)/4*255).astype(np.uint8)
Image.fromarray(np.hstack([rgb, np.stack([vis]*3,-1), (np.stack([mask]*3,-1)*255).astype(np.uint8)])).save(sys.argv[2])
