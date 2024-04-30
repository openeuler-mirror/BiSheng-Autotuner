#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Autotuner's argument parser for resumable interface.
Copyright (C) 2021-2021, Huawei Technologies Co., Ltd. All rights reserved.
"""
import argparse
import unittest

from autotuner.resumable.main import create_parser
from autotuner.resumable.main import MAX_PARALLELISM


class ParserTest(unittest.TestCase):
    def setUp(self):
        self.parser = create_parser()

    def test_custom_search_space(self):
        parsed = self.parser.parse_args(['minimize'])
        self.assertIsNone(parsed.search_space, None)

        parsed = self.parser.parse_args(['minimize', '--search-space',
                                         '/path/to/search_space.yaml'])
        self.assertEqual(parsed.search_space, '/path/to/search_space.yaml')

    def test_max_parallelism(self):
        # Test the default value.
        parsed = self.parser.parse_args(['minimize'])
        self.assertEqual(parsed.trials, 1)

        # Test with MAX_PARALLELISM allowed.
        max_parallelism_str = str(MAX_PARALLELISM)
        parsed = self.parser.parse_args(['minimize', '--trials',
                                         max_parallelism_str])
        self.assertEqual(parsed.trials, MAX_PARALLELISM)

        # Tests with invalid values.
        parse_func = self.parser.parse_args
        with self.assertRaises(SystemExit):
            self.assertRaises(argparse.ArgumentTypeError, parse_func,
                            ['minimize', '--trials', '-1'])

        with self.assertRaises(SystemExit):
            self.assertRaises(argparse.ArgumentTypeError, parse_func,
                            ['minimize', '--trials', '0'])

        # Test with MAX_PARALLELISM + 1.
        with self.assertRaises(SystemExit):
            exceed = str(MAX_PARALLELISM + 1)
            self.assertRaises(argparse.ArgumentTypeError, parse_func,
                            ['minimize', '--trials', exceed])

    def test_use_baseline_config(self):
        """
        Verify the usage of '--use-baseline-config'.
        """
        parsed = self.parser.parse_args(['minimize'])
        self.assertFalse(parsed.use_baseline_config)

        parsed = self.parser.parse_args(['minimize', '--use-baseline-config'])
        self.assertTrue(parsed.use_baseline_config)

    def test_use_dynamic_values(self):
        parsed = self.parser.parse_args(['minimize'])
        self.assertFalse(parsed.use_dynamic_values)

        parsed = self.parser.parse_args(['minimize', '--use-dynamic-values'])
        self.assertTrue(parsed.use_dynamic_values)

