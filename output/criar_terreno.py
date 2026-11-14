"""Execute no Blender: blender --background --python output/criar_terreno.py.
Malha regular: indice = j * NX + i; X cresce em i, Y cresce em j; Z em metros.
Displacement procedural aplicado diretamente aos vertices (sem dependencia de shader).
"""
import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

OUT = Path(__file__).resolve().parent if '__file__' in globals() else Path('/media/samuel/LinuxData/projetos/blender/output')
OUT.mkdir(parents=True, exist_ok=True)
scene = bpy.data.scenes.new('Marte_Tres_Vias')
bpy.context.window.scene = scene
def enum_set(owner, key, value):
    values = [v.identifier for v in owner.bl_rna.properties[key].enum_items]
    if value not in values:
        raise ValueError((key, value, values))
    setattr(owner, key, value)
enum_set(scene.unit_settings, 'system', 'METRIC')
scene.unit_settings.scale_length = 1.0
def collection(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c
geo = collection('01_Terreno_Analise')
annotations = collection('02_Vias_Guias_Visuais')
studio = collection('03_Camera_Luzes')
def obj(name, data, col):
    o = bpy.data.objects.new(name, data)
    col.objects.link(o)
    return o
NX, NY, STEP = 193, 129, 0.125
routes = [('A', -8., 35., .22, (0.85,.075,.035,1)),
          ('B', 0., 15., .10, (1.,.58,.055,1)),
          ('C', 8., 5., .025, (.10,.75,.55,1))]
def parameters(x):
    if x <= -6: return 35., .22
    if x < -2:
        t = (x+6)/4; t = t*t*(3-2*t)
        return 35*(1-t)+15*t, .22*(1-t)+.10*t
    if x <= 2: return 15., .10
    if x < 6:
        t = (x-2)/4; t = t*t*(3-2*t)
        return 15*(1-t)+5*t, .10*(1-t)+.025*t
    return 5., .025
def height(x,y):
    angle, amplitude = parameters(x)
    # Envelope anula o detalhe nas extremidades: desnível longitudinal exato.
    envelope = math.sin(math.pi*y/16)**2
    detail = (.55*math.sin(2.1*x+1.2*y)*math.cos(1.7*y-.4*x)
              + .3*math.sin(4.3*x+3.2*y) + .15*math.cos(6.7*x-4.8*y))
    return y*math.tan(math.radians(angle)) + amplitude*envelope*detail
verts = [(i*STEP-12,j*STEP,height(i*STEP-12,j*STEP)) for j in range(NY) for i in range(NX)]
faces = [(j*NX+i,j*NX+i+1,(j+1)*NX+i+1,(j+1)*NX+i) for j in range(NY-1) for i in range(NX-1)]
mesh = bpy.data.meshes.new('Grade_193x129_Quads')
mesh.from_pydata(verts, [], faces)
mesh.update()
terrain = obj('Terreno_Heightmap', mesh, geo)
terrain['nx'], terrain['ny'], terrain['spacing_m'] = NX, NY, STEP
terrain['index_order'] = 'j * nx + i; x=-12+i*spacing; y=j*spacing; height=vertex.co.z'
terrain['displacement'] = 'Deterministic analytic height displacement baked into editable vertices'
terrain['route_width_m'] = 4.0
terrain['inclination_definition'] = 'Longitudinal mean rise/run over 16 m along +Y; local slopes vary'
for key, center, angle, amplitude, color in routes:
    group = terrain.vertex_groups.new(name='Via_'+key)
    group.add([i for i,v in enumerate(verts) if abs(v[0]-center)<=2],1.0,'REPLACE')
    terrain['Via_'+key+'_angle_deg'] = angle
uv = mesh.uv_layers.new(name='UV_Regular')
for p in mesh.polygons:
    p.use_smooth = True
    for li in p.loop_indices:
        v = verts[mesh.loops[li].vertex_index]
        uv.data[li].uv = ((v[0]+12)/24, v[1]/16)
mask = mesh.attributes.new('rock_weight','FLOAT','POINT')
for i,(x,y,z) in enumerate(verts):
    mask.data[i].value = (parameters(x)[0]-5)/40+.15
mat = bpy.data.materials.new('Solo_e_Rocha_Procedural')
mat.use_nodes = True
n = mat.node_tree.nodes; n.clear(); l = mat.node_tree.links
output = n.new('ShaderNodeOutputMaterial')
soil = n.new('ShaderNodeBsdfPrincipled'); soil.inputs['Base Color'].default_value=(.32,.105,.045,1); soil.inputs['Roughness'].default_value=.92
rock = n.new('ShaderNodeBsdfPrincipled'); rock.inputs['Base Color'].default_value=(.105,.065,.045,1); rock.inputs['Roughness'].default_value=.83
tex = n.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value=3.8; tex.inputs['Detail'].default_value=3
coord = n.new('ShaderNodeTexCoord'); l.new(coord.outputs['Object'],tex.inputs['Vector'])
attr = n.new('ShaderNodeAttribute'); attr.attribute_name='rock_weight'
multiply = n.new('ShaderNodeMath'); enum_set(multiply,'operation','MULTIPLY'); l.new(attr.outputs['Fac'],multiply.inputs[0]); l.new(tex.outputs['Fac'],multiply.inputs[1])
ramp=n.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position=.13; ramp.color_ramp.elements[1].position=.45; l.new(multiply.outputs[0],ramp.inputs[0])
mix=n.new('ShaderNodeMixShader'); l.new(ramp.outputs[0],mix.inputs[0]); l.new(soil.outputs[0],mix.inputs[1]); l.new(rock.outputs[0],mix.inputs[2]); l.new(mix.outputs[0],output.inputs['Surface'])
for node,loc in [(coord,(-800,0)),(tex,(-600,0)),(attr,(-600,250)),(multiply,(-350,200)),(ramp,(-150,250)),(soil,(-150,-100)),(rock,(100,-100)),(mix,(400,150)),(output,(620,150))]: node.location=loc
mesh.materials.append(mat)
def simple_material(name, color):
    m=bpy.data.materials.new(name); m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=color
    p.inputs['Roughness'].default_value=.7
    return m
def line(name,points,material,radius=.035):
    c=bpy.data.curves.new(name,'CURVE'); c.dimensions='3D'; c.bevel_depth=radius; c.bevel_resolution=2
    s=c.splines.new('POLY'); s.points.add(len(points)-1)
    for p,co in zip(s.points,points): p.co=(*co,1)
    o=obj(name,c,annotations); c.materials.append(material); return o
for key,cx,angle,amp,color in routes:
    m=simple_material('Guia_'+key,color)
    for side in [-2,2]:
        line('Limite_'+key,[(cx+side,j*STEP,height(cx+side,j*STEP)+.055) for j in range(NY)],m,.023)
    for j in range(16):
        line('Direcao_'+key,[(cx,y,height(cx,y)+.07) for y in [j+.15+k*.1 for k in range(6)]],m,.045)
    font=bpy.data.curves.new('Legenda_'+key,'FONT'); font.body=f'VIA {key}  /  {angle:.0f}°'; font.size=.65
    enum_set(font,'align_x','CENTER')
    o=obj('Legenda_'+key,font,annotations); o.location=(cx,-1.2,.12); font.materials.append(m)
camera_data=bpy.data.cameras.new('Camera'); camera=obj('Camera',camera_data,studio)
camera.location=(25,-32,30); camera.rotation_euler=(Vector((0,7,4.5))-camera.location).to_track_quat('-Z','Y').to_euler()
enum_set(camera_data,'type','ORTHO'); camera_data.ortho_scale=43
scene.camera=camera
for o in annotations.objects:
    if o.type=='FONT': o.rotation_euler=camera.rotation_euler
for name,position,power,size in [('Key',(-10,-5,24),2600,15),('Fill',(18,8,20),1800,12)]:
    d=bpy.data.lights.new(name,'AREA'); d.energy=power; d.shape='DISK'; d.size=size
    o=obj(name,d,studio); o.location=position; o.rotation_euler=(Vector((0,8,1))-o.location).to_track_quat('-Z','Y').to_euler()
sun=bpy.data.lights.new('Sol','SUN'); sun.energy=2.0; sun.angle=.15
o=obj('Sol',sun,studio); o.rotation_euler=(.4,-.5,-.4)
world=bpy.data.worlds.new('Ceu'); world.use_nodes=True
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND'); bg.inputs['Color'].default_value=(.065,.08,.11,1); bg.inputs['Strength'].default_value=.45
scene.world=world
try: scene.render.engine='CYCLES'
except TypeError as e: raise RuntimeError(str(e))
scene.cycles.samples=32; scene.cycles.use_denoising=True
scene.render.resolution_x=1400; scene.render.resolution_y=1000; scene.render.resolution_percentage=100
enum_set(scene.render.image_settings,'file_format','PNG')
scene.render.filepath=str(OUT/'terreno_marciano.png')
bpy.context.view_layer.objects.active=terrain; terrain.select_set(True)
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_perspective='CAMERA'
report={'grid':[NY,NX],'vertices':len(mesh.vertices),'quads':len(mesh.polygons),'spacing_m':STEP,'extent_m':[24,16], 'routes':{}}
for key,cx,angle,amp,color in routes:
    i=round((cx+12)/STEP)
    z=[mesh.vertices[j*NX+i].co.z for j in range(NY)]
    measured=math.degrees(math.atan2(z[-1]-z[0],16))
    assert abs(measured-angle)<.001
    report['routes'][key]={'center_x_m':cx,'width_m':4,'rise_m':z[-1]-z[0],'longitudinal_angle_deg':measured,'local_longitudinal_angle_range_deg':[min(math.degrees(math.atan2(b-a,STEP)) for a,b in zip(z,z[1:])),max(math.degrees(math.atan2(b-a,STEP)) for a,b in zip(z,z[1:]))]}
assert len(mesh.vertices)==NX*NY and all(len(p.vertices)==4 for p in mesh.polygons)
(OUT/'validacao.json').write_text(json.dumps(report,indent=2))
txt=bpy.data.texts.new('LEIA_ME'); txt.write('Terreno_Heightmap: unica malha para analise. Unidades: metros. Grade NY=129, NX=193, passo=0.125 m. Indice j*NX+i. Origem XY=(-12,0). Z real, sem modificadores. Vias A/B/C: centros X=-8/0/8; largura=4 m; sentido +Y. Angulos longitudinais medios: 35/15/5 graus; rugosidade varia localmente. Guias sao objetos visuais separados. Transicoes entre faixas possuem declividade transversal. Nao sao tres rotas para um mesmo destino. Displacement analitico aplicado aos vertices; materiais procedurais misturados por atributo e ruido. Sem Sobel ou ML. Script externo criar_terreno.py reproduz a cena.\n'+json.dumps(report,indent=2))
if '__file__' in globals():
    source=bpy.data.texts.new('criar_terreno.py'); source.write(Path(__file__).read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'terreno_marciano.blend'))
print(json.dumps(report))
