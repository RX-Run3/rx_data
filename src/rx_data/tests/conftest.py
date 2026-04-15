'''
This module is needed to control how pytest will run tests
'''
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
