# -*- coding: utf-8 -*-

# ocitysmap, city map and street index generator from OpenStreetMap data
# Copyright (C) 2010  David Decotigny
# Copyright (C) 2010  Frédéric Lehobey
# Copyright (C) 2010  Pierre Mauduit
# Copyright (C) 2010  David Mentré
# Copyright (C) 2010  Maxime Petazzoni
# Copyright (C) 2010  Thomas Petazzoni
# Copyright (C) 2010  Gaël Utard

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import pango
import cairo

import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import draw_utils

class IndexEmptyError(Exception):
    """This exception is raised when no data is to be rendered in the index."""
    pass

class IndexDoesNotFitError(Exception):
    """This exception is raised when the index does not fit in the given
    graphical area, even after trying smaller font sizes."""
    pass

class IndexCategory:
    """
    The IndexCategory represents a set of index items that belong to the same
    category (their first letter is the same or they are of the same amenity
    type).
    """
    name = None
    icon = None
    items = None

    def __init__(self, name, items = None, icon=None):
        assert name is not None
        self.name  = name
        self.items = items or list()
        self.icon = icon

    def __str__(self):
        return '<%s (%s)>' % (self.name, map(str, self.items))

    def __repr__(self):
        return 'IndexCategory(%s, %s)' % (repr(self.name),
                                          repr(self.items))

    def draw(self, rtl, ctx, pc, layout, fascent, fheight,
             baseline_x, baseline_y):
        """Draw this category header.

        Args:
            rtl (boolean): whether to draw right-to-left or not.
            ctx (cairo.Context): the Cairo context to draw to.
            pc (pangocairo.CairoContext): the PangoCairo context.
            layout (pango.layout): the Pango layout to draw text into.
            fascent (int): font ascent.
            fheight (int): font height.
            baseline_x (int): base X axis position.
            baseline_y (int): base Y axis position.
        """

        ctx.save()
        ctx.set_source_rgb(0.9, 0.9, 0.9)
        ctx.rectangle(baseline_x, baseline_y - fascent,
                      layout.get_width() / pango.SCALE, fheight)
        ctx.fill()

        ctx.set_source_rgb(0.0, 0.0, 0.0)
        lx, _, rx, _ = draw_utils.draw_text_center(ctx, pc, layout, fascent, fheight,
                                    baseline_x, baseline_y, self.name)
        
        if self.icon:
            ctx.save()
            grp, w, h = self.draw_icon(ctx, fheight)
            if grp:
                ctx.translate(lx - (w * 1.1), baseline_y - fascent + (fheight-h)/2.0)
                ctx.set_source(grp)
                ctx.paint_with_alpha(1.0)
            ctx.restore()   

        ctx.restore()

    def draw_icon(self, ctx, fheight):
        if not os.path.exists(self.icon):
            print "WARNING: Icon not found:", self.icon
            return None, None

        with open(self.icon, 'rb') as f:
            png = cairo.ImageSurface.create_from_png(f)

        ctx.push_group()
        ctx.save()
        ctx.move_to(0, 0)
        # resize icon down if necessary but not up
        factor = min(fheight, png.get_height()) / png.get_height()
        ctx.scale(factor, factor)
        ctx.set_source_surface(png)
        ctx.paint()
        ctx.restore()
        return ctx.pop_group(), png.get_width()*factor, min(fheight, png.get_height())

    def get_all_item_labels(self):
        return [x.label for x in self.items]

    def get_all_item_squares(self):
        return [x.squares for x in self.items]


class IndexItem:
    """
    An IndexItem represents one item in the index (a street or a POI). It
    contains the item label (street name, POI name or description) and the
    humanized squares description.
    """
    __slots__    = ['label', 'endpoint1', 'endpoint2', 'location_str']
    label        = None # str
    endpoint1    = None # coords.Point
    endpoint2    = None # coords.Point
    location_str = None # str or None

    def __init__(self, label, endpoint1, endpoint2):
        assert label is not None
        self.label        = label
        self.endpoint1    = endpoint1
        self.endpoint2    = endpoint2
        self.location_str = None

    def __str__(self):
        return '%s...%s' % (self.label, self.location_str)

    def __repr__(self):
        return ('IndexItem(%s, %s, %s, %s)'
                % (repr(self.label), self.endpoint1, self.endpoint2,
                   repr(self.location_str)))

    def draw(self, rtl, ctx, pc, layout, fascent, fheight,
             baseline_x, baseline_y):
        """Draw this index item to the provided Cairo context. It prints the
        label, the squares definition and the dotted line, with respect to the
        RTL setting.

        Args:
            rtl (boolean): right-to-left localization.
            ctx (cairo.Context): the Cairo context to draw to.
            pc (pangocairo.PangoCairo): the PangoCairo context for text
                drawing.
            layout (pango.Layout): the Pango layout to use for text
                rendering, pre-configured with the appropriate font.
            fascent (int): font ascent.
            fheight (int): font height.
            baseline_x (int): X axis coordinate of the baseline.
            baseline_y (int): Y axis coordinate of the baseline.
        """

        ctx.save()
        if not rtl:
            for i,line in enumerate(self.label.split('\n')):
                _, _, line_start, new_baseline_y = draw_utils.draw_text_left(ctx, pc, layout,
                                                             fascent, fheight,
                                                             baseline_x, baseline_y,
                                                             line)
                prev_baseline_y = baseline_y
                baseline_y = new_baseline_y
            
            line_end, _, _, _ = draw_utils.draw_text_right(ctx, pc, layout,
                                                        fascent, fheight,
                                                        baseline_x, prev_baseline_y,
                                                        self.location_str or '???')
        else:
            orig_baseline_y = baseline_y
            _, _, line_start, _ = draw_utils.draw_text_left(ctx, pc, layout,
                                                         fascent, fheight,
                                                         baseline_x, baseline_y,
                                                         self.location_str or '???')
            for i,line in enumerate(self.label.split('\n')):
                line_end, _, _, new_baseline_y = draw_utils.draw_text_right(ctx, pc, layout,
                                                            fascent, fheight,
                                                            baseline_x, baseline_y,
                                                            line)
                prev_baseline_y = baseline_y
                baseline_y = new_baseline_y

            prev_baseline_y = orig_baseline_y

        draw_utils.draw_dotted_line(ctx, max(fheight/12, 1),
                                    line_start + fheight/4, prev_baseline_y,
                                    line_end - line_start - fheight/2)
        ctx.restore()
        return i+1

    def update_location_str(self, grid):
        """
        Update the location_str field from the given Grid object.

        Args:
           grid (ocitysmap2.Grid): the Grid object from which we
           compute the location strings

        Returns:
           Nothing, but the location_str field will have been altered
        """
        if self.endpoint1 is not None:
            ep1_label = grid.get_location_str( * self.endpoint1.get_latlong())
        else:
            ep1_label = None
        if self.endpoint2 is not None:
            ep2_label = grid.get_location_str( * self.endpoint2.get_latlong())
        else:
            ep2_label = None
        if ep1_label is None:
            ep1_label = ep2_label
        if ep2_label is None:
            ep2_label = ep1_label

        if ep1_label == ep2_label:
            if ep1_label is None:
                self.location_str = "???"
            self.location_str = ep1_label
        elif grid.rtl:
            self.location_str = "%s-%s" % (max(ep1_label, ep2_label),
                                           min(ep1_label, ep2_label))
        else:
            self.location_str = "%s-%s" % (min(ep1_label, ep2_label),
                                           max(ep1_label, ep2_label))


if __name__ == "__main__":
    import cairo
    import pangocairo

    surface = cairo.PDFSurface('/tmp/idx_commons.pdf', 1000, 1000)

    ctx = cairo.Context(surface)
    pc = pangocairo.CairoContext(ctx)

    font_desc = pango.FontDescription('DejaVu')
    font_desc.set_size(12 * pango.SCALE)

    layout = pc.create_layout()
    layout.set_font_description(font_desc)
    layout.set_width(200 * pango.SCALE)

    font = layout.get_context().load_font(font_desc)
    font_metric = font.get_metrics()

    fascent = font_metric.get_ascent() / pango.SCALE
    fheight = ((font_metric.get_ascent() + font_metric.get_descent())
               / pango.SCALE)

    first_item  = IndexItem('First Item', None, None)
    second_item = IndexItem('Second Item', None, None)
    category    = IndexCategory('Hello world !', [first_item, second_item])

    category.draw(False, ctx, pc, layout, fascent, fheight,
                  72, 80)
    first_item.draw(False, ctx, pc, layout, fascent, fheight,
                    72, 100)
    second_item.draw(False, ctx, pc, layout, fascent, fheight,
                     72, 120)

    surface.finish()
    print "Generated /tmp/idx_commons.pdf"
