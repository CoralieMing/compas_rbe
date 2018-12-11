from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from compas.utilities import i_to_blue
from compas.utilities import i_to_red
from compas.utilities import color_to_colordict

import compas_rhino

from compas_rhino.artists import MeshArtist
from compas_rhino.artists import NetworkArtist


__all__ = ['AssemblyArtist', 'BlockArtist']


class AssemblyArtist(NetworkArtist):
    """An artist for visualisation of assemblies inn Rhino.

    Parameters
    ----------
    assembly : compas_rbe.datastructures.Assembly
        The assembly data structure.
    layer : str, optional
        The base layer for drawing.
        Default is ``None``, which means drawing in the current layer.

    Examples
    --------
    .. code-block:: python

        pass

    """

    def __init__(self, assembly, layer=None):
        super(AssemblyArtist, self).__init__(assembly, layer=layer)
        self.defaults.update({
            'color.vertex' : (0, 0, 0),
            'color.vertex:is_support' : (255, 0, 0),
            'color.edge' : (0, 0, 0),
            'color.interface' : (255, 255, 255),
            'color.force:compression' : (0, 0, 255),
            'color.force:tension' : (255, 0, 0),
            'color.selfweight' : (0, 255, 0),

            'scale.force' : 0.1,
            'scale.selfweight' : 0.1,

            'eps.selfweight' : 1e-3,
            'eps.force' : 1e-3,
        })

    @property
    def assembly(self):
        """Assembly : the assembly data structure."""
        return self.datastructure

    @assembly.setter
    def assembly(self, assembly):
        self.datastructure = assembly

    def clear_(self, name):
        name = "{}.{}.*".format(self.assembly.name, name)
        guids = compas_rhino.get_objects(name=name)
        compas_rhino.delete_objects(guids)

    def clear_blocks(self):
        self.clear_('block')

    def clear_interfaces(self):
        self.clear_('interface')

    def clear_forces(self):
        self.clear_('force')

    def clear_selfweight(self):
        self.clear_('selfweight')

    def draw_blocks(self, show_faces=False, show_vertices=False):
        """Draw the blocks of the assembly.

        Parameters
        ----------
        show_faces : bool, optional
            Draw the faces of the block.
            Default is ``False``.
        show_vertices : bool, optional
            Draw the vertices of the block.
            Default is ``False``.

        Notes
        -----
        * By default, blocks are drawn as wireframes.
        * By default, blocks are drawn on a sublayer of the base layer, if a base layer was specified.
        * Block names have the following pattern: ``"{assembly_name}.block.{block_id}"``
        * Faces and vertices can be drawn using the corresponding flags.
        * Block components have the following pattern:

          * face: ``"{assembly_name}.block.{block_id}.face.{face_id}"``
          * edge: ``"{assembly_name}.block.{block_id}.edge.{edge_id}"``
          * vertex: ``"{assembly_name}.block.{block_id}.vertex.{vertex_id}"``


        Examples
        --------
        .. code-block:: python

            pass

        """
        layer = "{}::Blocks".format(self.layer) if self.layer else None
        artist = BlockArtist(None, layer=layer)
        for key, attr in self.assembly.vertices(True):
            block = self.assembly.blocks[key]
            block.name = "{}.block.{}".format(self.assembly.name, key)
            artist.block = block
            artist.draw_edges()
            if show_faces:
                artist.draw_faces()
            if show_vertices:
                artist.draw_vertices()
        artist.redraw()

    def draw_blockfacenormals(self):
        pass

    def draw_interfaces(self, keys=None, color=None):
        """Draw the interfaces between the blocks.

        Parameters
        ----------
        keys : list
            A list of interface identifiers (i.e. assembly edge (u, v) tuples).
            Default is ``None``, in which case all interfaces are drawn.
        color : str, tuple, dict
            The color specififcation for the interfaces.
            Colors should be specified in the form of a string (hex colors) or
            as a tuple of RGB components.
            To apply the same color to all interfaces, provide a single color
            specification. Individual colors can be assigned using a dictionary
            of key-color pairs. Missing keys will be assigned the default interface
            color (``self.defaults['color.interface']``).
            The default is ``None``, in which case all interfaces are assigned the
            default interface color.

        Notes
        -----
        * Interfaces are drawn as mesh faces.
        * Interfaces are drawn on a sub-layer *Interfaces* of the base layer, if a base layer was provided.
        * Interface names have the following pattern: ``"{assembly_name}.interface.{from block_id}-{to block_id}"``
        * Interfaces have a direction, as suggested by the naming convention.

        """
        layer = "{}::Interfaces".format(self.layer) if self.layer else None
        faces = []

        keys = keys or list(self.assembly.edges())
        colordict = color_to_colordict(color,
                                       keys,
                                       default=self.defaults.get('color.interface'),
                                       colorformat='rgb',
                                       normalize=False)

        for u, v, attr in self.assembly.edges(True):
            faces.append({
                'points': attr['interface_points'],
                'name'  : "{}.interface.{}-{}".format(self.assembly.name, u, v),
                'color' : colordict[(u, v)]
            })
        compas_rhino.xdraw_faces(faces, layer=layer, clear=False, redraw=False)

    def draw_iframes(self):
        pass

    def draw_forces(self, scale=None, eps=None):
        """Draw the contact forces at the interfaces.

        Parameters
        ----------
        scale : float, optional
            The scale at which the forces should be drawn.
            Default is `0.1`.
        eps : float, optional
            A tolerance for drawing small force vectors.
            Force vectors with a scaled length smaller than this tolerance are not drawn.
            Default is `1e-3`.

        Notes
        -----
        * Forces are drawn as lines with arrow heads.
        * Forces are drawn on a sub-layer *Forces* of the base layer, if a base layer was specified.
        * At every interface point there can be a *compression* force (blue) and a *tension* force (red).
        * Forces are named according to the following pattern: ``"{assembly_name}.force.{from block}-{to block}.{interface point}"``

        """
        layer = "{}::Forces".format(self.layer) if self.layer else None
        scale = scale or self.defaults['scale.force']
        eps = eps or self.defaults['eps.force']
        color_compression = self.defaults['color.force:compression']
        color_tension = self.defaults['color.force:tension']

        lines = []

        for a, b, attr in self.assembly.edges(True):
            if attr['interface_forces'] is None:
                continue

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
                        'color' : color_compression,
                        'name'  : "{0}.force.{1}-{2}.{3}".format(self.assembly.name, a, b, i),
                        'arrow' : 'end'
                    })
                if scale * c_nn > eps:
                    # tension force
                    lines.append({
                        'start' : sp,
                        'end'   : [sp[axis] - scale * c_nn * w[axis] for axis in range(3)],
                        'color' : color_tension,
                        'name'  : "{0}.force.{1}-{2}.{3}".format(self.assembly.name, a, b, i),
                        'arrow' : 'end'
                    })

        compas_rhino.xdraw_lines(lines, layer=layer, clear=False, redraw=False)

    def draw_selfweight(self, scale=None, eps=None):
        """Draw vectors indicating the magnitude of the selfweight of the blocks.

        Parameters
        ----------
        scale : float, optional
            The scale at which the selfweight vectors should be drawn.
            Default is `0.1`.
        eps : float, optional
            A tolerance for drawing small vectors.
            Selfweight vectors with a scaled length smaller than this tolerance are not drawn.
            Default is `1e-3`.

        Notes
        -----
        * Selfweight vectors are drawn as Rhino lines with arrow heads.
        * The default color is *green*: `'#00ff00'` or `(0, 255, 0)`.
        * Selfweight vectors are drawn in a sub-layer *Selfweight* of the base layer, if a base layer was specified.
        * Selfweight vectors are named according to the following pattern: `"{assembly name}.selfweight.{block id}"`.

        """
        layer = "{}::Selfweight".format(self.layer) if self.layer else None
        scale = scale or self.defaults['scale.selfweight']
        eps = eps or self.defaults['eps.selfweight']
        color = self.defaults['color.selfweight']

        lines = []

        for key, attr in self.assembly.vertices(True):
            block = self.assembly.blocks[key]
            volume = block.volume()

            if volume * scale < eps:
                continue

            vector = [0.0, 0.0, -1.0 * volume * scale]

            sp = block.centroid()
            ep = sp[:]
            ep[2] += vector[2]

            lines.append({
                'start' : sp,
                'end'   : ep,
                'name'  : "{}.selfweight.{}".format(self.assembly.name, key),
                'color' : (0, 255, 0),
                'arrow' : 'end'
            })

        compas_rhino.xdraw_lines(lines, layer=layer, clear=False, redraw=False)

    def color_interfaces(self):
        for u, v, attr in self.assembly.edges(True):
            if attr['interface_forces'] is None:
                continue

            name = "{}.interface.{}-{}".format(self.assembly.name, u, v)
            guids = compas_rhino.get_objects(name=name)
            if not guids:
                continue

            guid = guids[0]

            call_np = [force['c_np'] for force in attr['interface_forces']]
            call_nn = [force['c_nn'] for force in attr['interface_forces']]
            cmax_np, cmax_nn = max(call_np), max(call_nn)
            cmin_np = cmin_nn = 0

            colors = []
            cvalues = []
            for i in range(len(attr['interface_points'])):
                c_np = attr['interface_forces'][i]['c_np']
                c_nn = attr['interface_forces'][i]['c_nn']
                if c_np < 1e-3:
                    red = i_to_red((c_nn - cmin_nn) / (cmax_nn - cmin_nn + 0.0001))
                    colors.append(red)
                else:
                    blue = i_to_blue((c_np - cmin_np) / (cmax_np - cmin_np + 0.0001))
                    cvalues.append((c_np - cmin_np) / (cmax_np - cmin_np + 0.0001))
                    colors.append(blue)

            # making the center point color as average vertices
            if len(attr['interface_points']) > 4:
                blue = i_to_blue(sum(cvalues) / len(cvalues))
                colors.append(blue)

            compas_rhino.set_mesh_vertex_colors(guid, colors)


class BlockArtist(MeshArtist):

    def __init__(self, *args, **kwargs):
        super(BlockArtist, self).__init__(*args, **kwargs)
        self.defaults.update({

        })

    @property
    def block(self):
        return self.datastructure

    @block.setter
    def block(self, block):
        self.datastructure = block


# ==============================================================================
# Debugging
# ==============================================================================

if __name__ == "__main__":
    pass
