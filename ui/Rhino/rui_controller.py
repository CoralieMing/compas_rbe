import os
import ast

import compas_rhino
import compas_rbe

from compas.utilities import XFunc
from compas_rbe.cad.rhino import Assembly
from compas_rhino.helpers import NetworkArtist
from compas_rhino.helpers import MeshArtist

HERE = os.path.dirname(__file__)

identify_interfaces_ = XFunc('compas_rbe.rbe.interfaces.identify_interfaces_xfunc')
identify_interfaces_.tmpdir = compas_rbe.TEMP

compute_interface_forces_ = XFunc('compas_rbe.rbe.equilibrium.compute_interface_forces_xfunc')
compute_interface_forces_.tmpdir = compas_rbe.TEMP


__author__    = ['Tom Van Mele', ]
__copyright__ = 'Copyright 2016, Block Research Group - ETH Zurich'
__license__   = 'MIT License'
__email__     = 'vanmelet@ethz.ch'


class RBEMacroController(object):

    instancename = 'rbe'

    def __init__(self):
        self.assembly = None
        self.settings = {
            'color.assembly.vertex' : (0, 0, 0),
            'color.assembly.edge'   : (0, 0, 0),
            'color.block.vertex'    : (0, 255, 0),
            'color.block.edge'      : (255, 255, 255),
            'color.block.face'      : (200, 200, 200),
            'color.interface'       : (255, 255, 255),
            'color.compression'     : (0, 0, 255),
            'color.tension'         : (255, 0, 0),
            'color.friction'        : (),
            'color.selfweight'      : (0, 0, 0),

            'visibility.assembly.vertices'   : False,
            'visibility.assembly.edges'      : False,
            'visibility.blocks.vertices'     : False,
            'visibility.blocks.edges'        : True,
            'visibility.blocks.faces'        : False,
            'visibility.blocks.selfweight'   : False,
            'visibility.interfaces'          : True,
            'visibility.interfaces.forces'   : False,
            'visibility.interfaces.friction' : False,

            'scale.interfaces.forces' : 1.0,

            'eps.interfaces.forces' : 0.001,

            'compute_interface_forces.verbose'   : True,
            'compute_interface_forces.max_iters' : 100,
        }

    def init(self):
        pass

    # text => settings
    def update_settings(self):
        names  = sorted(self.settings.keys())
        values = [str(self.settings[name]) for name in names]
        values = compas_rhino.update_named_values(names, values)
        if values:
            for name, value in zip(names, values):
                try:
                    self.settings[name] = ast.literal_eval(value)
                except (TypeError, ValueError):
                    self.settings[name] = value
            self.update_view()

    # text => view
    def update_view(self):
        # assembly
        nartist = NetworkArtist(self.assembly, layer="DEA::Assembly")
        nartist.clear_layer()
        if self.settings['visibility.assembly.edges']:
            nartist.draw_edges()
        if self.settings['visibility.assembly.vertices']:
            nartist.draw_vertices()
        nartist.redraw()
        # blocks
        martist = MeshArtist(None, layer="DEA::Blocks")
        martist.clear_layer()
        for key in self.assembly.vertices():
            martist.datastructure = self.assembly.blocks[key]
            if self.settings['visibility.blocks.faces']:
                martist.draw_faces(join_faces=True)
            if self.settings['visibility.blocks.edges']:
                martist.draw_edges()
            if self.settings['visibility.blocks.vertices']:
                martist.draw_vertices()
        martist.redraw()
        # interfaces
        compas_rhino.clear_layer('DEA::interfaces')
        if self.settings['visibility.interfaces']:
            faces = []
            for u, v, attr in self.assembly.edges(True):
                points = attr['interface_points'] + attr['interface_points'][0:1]
                faces.append({
                    'points': points,
                    'name'  : '{0}.interface.{1}-{2}'.format(self.assembly.name, u, v),
                    'color' : self.settings['color.interface']
                })
            compas_rhino.xdraw_faces(faces, layer="DEA::Interfaces")
        # interface forces
        compas_rhino.clear_layer('DEA::Forces')
        if self.settings['visibility.interfaces.forces']:
            scale = self.settings['scale.interfaces.forces']
            eps   = self.settings['eps.interfaces.forces']
            lines = []
            for u, v, attr in self.assembly.edges(True):
                if attr['interface_forces']:
                    w = attr['interface_uvw'][2]
                    for i in range(len(attr['interface_points'])):
                        sp   = attr['interface_points'][i]
                        c_np = attr['interface_forces'][i]['c_np']
                        c_nn = attr['interface_forces'][i]['c_nn']
                        if scale * c_np > eps:
                            # compression force
                            lines.append({
                                'start' : sp,
                                'end'   : [sp[axis] + scale * c_np * w[axis] for axis in range(3)],
                                'color' : self.settings['color.compression'],
                                'name'  : '{0}.force.{1}-{2}.{3}'.format(self.assembly.name, u, v, i),
                                'arrow' : 'end'
                            })
                        if scale * c_nn > eps:
                            # tension force
                            lines.append({
                                'start' : sp,
                                'end'   : [sp[axis] - scale * c_nn * w[axis] for axis in range(3)],
                                'color' : self.settings['color.tension'],
                                'name'  : '{0}.force.{1}-{2}.{3}'.format(self.assembly.name, u, v, i),
                                'arrow' : 'end'
                            })
            compas_rhino.xdraw_lines(lines, layer="DEA::Forces")
        if self.settings['visibility.interfaces.friction']:
            pass

    # --------------------------------------------------------------------------
    # blocks
    # --------------------------------------------------------------------------

    # text => from_polys
    def blocks_from_polysurfaces(self):
        guids = compas_rhino.select_surfaces()
        self.assembly = Assembly.from_polysurfaces(guids)
        self.update_view()

    # text => from_meshes
    def blocks_from_meshes(self):
        guids = compas_rhino.select_meshes()
        self.assembly = Assembly.from_meshes(guids)
        self.update_view()

    # --------------------------------------------------------------------------
    # assembly
    # --------------------------------------------------------------------------

    # text => assembly_v@
    def assembly_edit_vertex_attributes(self):
        keys = self.assembly.select_vertices()
        if not keys:
            return
        names = sorted(self.assembly.default_vertex_attributes.keys())
        if self.assembly.update_vertex_attributes(keys, names):
            self.update_view()

    # text => assembly_e@
    def assembly_edit_edge_attributes(self):
        keys = self.assembly.select_edges()
        if not keys:
            return
        names = sorted(self.assembly.default_edge_attributes.keys())
        if self.assembly.update_edge_attributes(keys, names):
            self.update_view()

    # text => assembly_v#
    def assembly_show_vertex_labels(self):
        pass

    def assembly_hide_vertex_labels(self):
        pass

    # text => assembly_e#
    def assembly_show_edge_labels(self):
        pass

    def assembly_hide_edge_labels(self):
        pass

    def assembly_move_vertex(self):
        pass

    # --------------------------------------------------------------------------
    # rbe
    # --------------------------------------------------------------------------

    def identify_interfaces(self):
        data = {
            'assembly': self.assembly.to_data(),
            'blocks'  : {str(key): self.assembly.blocks[key].to_data() for key in self.assembly.blocks},
        }
        result = identify_interfaces_(data)
        self.assembly.data = result['assembly']
        for key in self.assembly.blocks:
            self.assembly.blocks[key].data = result['blocks'][str(key)]
        self.update_view()

    def compute_interface_forces(self):
        data = {
            'assembly': self.assembly.to_data(),
            'blocks'  : {str(key): self.assembly.blocks[key].to_data() for key in self.assembly.blocks},
        }
        result = compute_interface_forces_(
            data,
            verbose=self.settings['compute_interface_forces.verbose'],
            max_iters=self.settings['compute_interface_forces.max_iters']
        )
        self.assembly.data = result['assembly']
        for key in self.assembly.blocks:
            self.assembly.blocks[key].data = result['blocks'][str(key)]
        self.update_view()


# ==============================================================================
# Debugging
# ==============================================================================

if __name__ == "__main__":

    pass
