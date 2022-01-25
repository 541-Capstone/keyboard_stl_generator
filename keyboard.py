
import argparse
import json
import math
import re
import logging
import os
import os.path

from solid import *
from solid.utils import *

from switch import Switch
from support import Support
from support_cutout import SupportCutout
from cell import Cell
from item_collection import ItemCollection
from rotation_collection import RotationCollection
from body import Body



class Keyboard():

    def __init__(self, parameter_dict = {}):
        self.logger = logging.getLogger('Keyboard')
        self.logger.setLevel(logging.INFO)

        # create console handler and set level to debug
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # create formatter
        formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')

        # add formatter to ch
        ch.setFormatter(formatter)

        self.logger.addHandler(ch)

        self.modifier_include_list = ['x', 'y', 'w', 'h', 'r', 'rx', 'ry']

        self.parameter_dict = parameter_dict

        self.default_parameter_dict = {
            'plate_only': True,
            'plate_supports': True,
            
            'x_build_size' : 200,
            'y_build_size' : 200,

            'kerf' : 0.00,

            'top_margin' : 8,
            'bottom_margin' : 8,
            'left_margin' : 8,
            'right_margin' : 8,
            'case_height' : 10,
            'plate_wall_thickness' : 2.0,
            'plate_thickness' : 1.511,
            'plate_corner_radius' : 4,

            'support_bar_height' : 3.0,
            'support_bar_width' : 1.0
        }

        self.build_attr_from_dict(self.default_parameter_dict)
        self.build_attr_from_dict(self.parameter_dict)


        self.build_x = math.floor(self.x_build_size / Cell.SWITCH_SPACING)
        self.build_y = math.floor(self.y_build_size / Cell.SWITCH_SPACING)

        self.switch_collection = ItemCollection()
        self.support_collection = ItemCollection()
        self.support_cutout_collection = ItemCollection()
        self.switch_rotation_collection = RotationCollection()
        self.support_rotation_collection = RotationCollection()
        self.support_cutout_rotation_collection = RotationCollection()

        self.switch_cutouts = union()
        self.switch_supports = union()
        self.switch_support_cutouts = union()
        self.rotate_switch_cutout_collection = union()
        self.rotate_support_collection = union()
        self.rotate_support_cutout_collection = union()

        self.section_list = [[]]


    def build_attr_from_dict(self, parameter_dict):
        for param in parameter_dict.keys():
             value = parameter_dict[param]

             setattr(self, param, value)
    
    
    def set_parameter_dict(self, parameter_dict):
        self.parameter_dict = parameter_dict
        self.build_attr_from_dict(self.parameter_dict)
    
    
    def get_param(self, paramaeter_name):

        if paramaeter_name in self.parameter_dict.keys():
            return self.parameter_dict[paramaeter_name]
        elif paramaeter_name in self.default_parameter_dict.keys():
            return self.default_parameter_dict[paramaeter_name]
        else:
            raise ValueError('No paramter exists with name %s' % (paramaeter_name))


    def process_keyboard_layout(self, keyboard_layout_dict):
        y = 0.0
        rotation = 0.0
        rx = 0.0
        ry = 0.0
        r_x_offset = 0.0
        r_y_offset = 0.0
        
        for row in keyboard_layout_dict:
            x = 0.0
            w = 1.0
            h = 1.0

            if type(row) == type([]):
                for col in row:               
                    if type(col) == type({}):

                        for key in col.keys():
                            modifier_type = key
                            
                            if modifier_type in self.modifier_include_list:
                                size = float(col[key])
                                if modifier_type == 'w':
                                    w = size
                                if modifier_type == 'h':
                                    h = size
                                if modifier_type == 'x':
                                    x += size
                                    r_x_offset = size
                                if modifier_type == 'y':
                                    y += size
                                    r_y_offset = size
                                if modifier_type == 'r':
                                    rotation = size
                                    y = 0
                                    x = 0
                                if modifier_type == 'rx':
                                    rx = size
                                if modifier_type == 'ry':
                                    ry = size
                        
                    else:
                        x_offset = x
                        y_offset = -(y)

                        # Create switch cutout and support object without rotation
                        if rotation == 0.0:
                            self.switch_collection.add_item(x_offset, y_offset, Switch(x_offset, y_offset, w, h, kerf = self.kerf))
                            self.support_collection.add_item(x_offset, y_offset, Support(x_offset, y_offset, w, h, self.plate_thickness, self.support_bar_height, self.support_bar_width))
                            self.support_cutout_collection.add_item(x_offset, y_offset, SupportCutout(x_offset, y_offset, w, h, self.plate_thickness, self.support_bar_height, self.support_bar_width))
                            
                            
                        # Create switch cutout and support object without rotation
                        elif rotation != 0.0:
                            self.switch_rotation_collection.add_item(rotation, x_offset, y_offset, Switch(x_offset, y_offset, w, h, kerf = self.kerf), rx, ry)
                            self.support_rotation_collection.add_item(rotation, x_offset, y_offset, Support(x_offset, y_offset,w, h, plate_thickness, support_bar_height, support_bar_width), rx, ry)

                        # Create normal switch support outline
                        # if rotation == 0.0:
                            
                            
                        # Create rotated switch support outline
                        # elif rotation != 0.0:
                            

                        x += w    
                        w = 1.0
                        h = 1.0

                y += 1

    def get_assembly(self):
        assembly = union()

        max_x, min_y = self.switch_collection.get_collection_bounds()

        self.switch_supports += self.support_collection.get_moved_union()
        self.switch_cutouts += self.switch_collection.get_moved_union()
        self.switch_support_cutouts += self.support_cutout_collection.get_moved_union()

        # Union together all switch cutouts 
        for rotation in self.switch_rotation_collection.get_rotation_list():
            self.rotate_switch_cutout_collection += self.switch_rotation_collection.get_rotated_moved_union(rotation)

        # Union together all support
        for rotation in self.support_rotation_collection.get_rotation_list():
            self.rotate_support_collection += self.support_rotation_collection.get_rotated_moved_union(rotation)

        self.switch_supports += self.rotate_support_collection
        self.switch_cutouts += self.rotate_switch_cutout_collection
        # self.switch_cutouts = switch_cutout(2.5)

        body = Body(self.top_margin, self.bottom_margin, self.left_margin, self.right_margin, self.case_height, self.plate_wall_thickness, self.plate_thickness, self.plate_corner_radius, self.plate_only, self.plate_supports)

        body.set_dimensions(max_x, min_y)
        assembly += body.case()

        assembly -= self.switch_support_cutouts
        assembly += self.switch_supports
        assembly -= self.switch_cutouts
        
        # assembly += section_objects
        # assembly = self.switch_cutouts

        return assembly


    def split_keybaord(self):
        max_x, min_y = self.switch_collection.get_collection_bounds()
        self.logger.info('max_x: %d, min_y: %d', max_x, min_y)
        self.logger.info('build_x: %d, build_y: %d', self.build_x, self.build_y)

        x_parts = math.ceil(max_x / self.build_x)
        y_parts = math.ceil(abs(min_y) / self.build_y)
        self.logger.info('x_parts: %d, y_parts: %d', x_parts, y_parts)

        x_per_part = math.ceil(max_x / x_parts)
        y_per_part = math.floor(min_y / y_parts)
        self.logger.info('x_per_part: %d, y_per_part: %d', x_per_part, y_per_part)

        # Union all standard switch cutouts together
        current_x_start = 0.0
        current_y_start = 0.0
        current_x_section = 0
        current_y_section = 0
        next_x_section = 0
        next_y_section = 0
        
        # build_area = left(self.left_margin) ( back(self.y_build_size - self.top_margin) ( down(10) ( cube([self.x_build_size, self.y_build_size, 10]) ) ) )

        switch_object_dict = self.switch_collection.get_collection_dict()
        for x in sorted(switch_object_dict.keys()):
            x_row = switch_object_dict[x]
            for y in x_row.keys():
                self.logger.debug('\tx: %d, y: %d', x, y)
                self.logger.debug('x_row.keys(): %s', str(x_row.keys()))
                # switch_cutouts += x_row[y].get_moved()
                w = x_row[y].w
                h = x_row[y].h
                
                switch_x_max = Cell.u(x + w) + self.left_margin
                switch_x_min = Cell.u(x) + self.left_margin
                switch_y_max = Cell.u(abs(y) + h) + self.top_margin
                switch_y_min = Cell.u(abs(y)) + self.top_margin

                temp_object = {
                    'x': x,
                    'y': y,
                    'w': w,
                    'h': h,
                    'switch_x_max': switch_x_max,
                    'switch_x_min': switch_x_min,
                    'switch_y_max': switch_y_max,
                    'switch_y_min': switch_y_min,
                    'accounted_for': False,
                    'object': x_row[y].get_moved()
                }

                if switch_x_max - current_x_start < self.x_build_size:
                    # self.logger.info('current_x_section:', current_x_section)
                    self.section_list[current_x_section].append(temp_object)
                elif switch_x_max - current_x_start > self.x_build_size and next_x_section > current_x_section:
                    self.section_list[next_x_section].append(temp_object)
                else:
                    # self.logger.info('switch_x_max:', switch_x_max, 'current_x_start:', current_x_start, 'switch_x_max - current_x_start:', switch_x_max - current_x_start, 'x_build_size:', x_build_size)
                    self.section_list.append([temp_object])
                    next_x_section = current_x_section + 1

                
                # self.logger.info('\tswitch_x: (', switch_x_min, ',', switch_x_max, '), switch_y: (', switch_y_min, switch_y_max, ')')
            
            if next_x_section > current_x_section:
                current_x_start = self.section_list[next_x_section][0]['switch_x_min']
                current_x_section = next_x_section