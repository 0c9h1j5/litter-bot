"""Stretch 3 리프트별 그리퍼 높이 (logs/2026-11-23_stretch3_lift_reach.md)"""
import sys, mujoco, numpy as np
m = mujoco.MjModel.from_xml_path(sys.argv[1])
d = mujoco.MjData(m)
print("sites:", [m.site(i).name for i in range(m.nsite)])
print("lift range", m.jnt_range[m.joint("joint_lift").id])
names=[m.joint(i).name for i in range(m.njnt)]
print(names)
def setq(name,v): d.qpos[m.jnt_qposadr[m.joint(name).id]]=v
for lift in (0.0,0.5,1.1):
  for pitch in (0.0,-1.57):
    mujoco.mj_resetData(m,d)
    setq("joint_lift",lift)
    if "joint_wrist_pitch" in names: setq("joint_wrist_pitch",pitch)
    mujoco.mj_forward(m,d)
    # lowest/highest point of finger pad geoms
    zs=[]
    for g in range(m.ngeom):
      b=m.body(m.geom_bodyid[g]).name
      if "finger" in b or "gripper" in b:
        zs.append(d.geom_xpos[g][2])
    sid=[i for i in range(m.nsite) if "grasp" in m.site(i).name or "center" in m.site(i).name]
    sp=[ (m.site(i).name, np.round(d.site_xpos[i],3).tolist()) for i in sid]
    print(f"lift={lift} pitch={pitch} gripper geom z min/max={min(zs):.3f}/{max(zs):.3f} sites={sp}")
