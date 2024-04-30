# coding=utf-8
"""
A set of tools to create/interact with the configuration database.
Copyright (C) 2017-2022, Huawei Technologies Co., Ltd. All rights reserved.
"""

from autotuner.models import CodeRegion
from autotuner.models import CodeRegionConfiguration
from autotuner.models import DebugLoc
from sqlalchemy import create_engine
from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Boolean
from sqlalchemy import PickleType
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Table declarations for the database
BASE_TABLE = declarative_base()


class OptimalConfig(BASE_TABLE):
    """
    Stores the parameters for a (hash, type, pass) triple
    during the tuning run.
    """
    __tablename__ = "optimalConfigs"
    hashcode = Column(String, primary_key=True)
    code_region_type = Column(String, primary_key=True)
    pass_name = Column(String, primary_key=True)
    params = Column(PickleType)


class CurrentCodeRegion(BASE_TABLE):
    """
    A temporary table of all code regions opportunities.
    Will be used to generate LLVM input.
    The primary key constraints must match CodeRegion::Operator== in LLVM.
    """
    __tablename__ = "currentCodeRegions"
    name = Column(String, primary_key=True)
    pass_name = Column(String, primary_key=True)
    func_name = Column(String, primary_key=True)
    code_region_type = Column(String, primary_key=True)
    hashcode = Column(String, primary_key=True)
    debug_file = Column(String, primary_key=True)
    debug_line = Column(String, primary_key=True)
    debug_column = Column(String, primary_key=True)
    invocation = Column(String, primary_key=True)
    seen = Column(Boolean)


def create_config_db_session(data_dir):
    """
    Creates `configs.db` in `data_dir` if it does not exist
    and creates a connection to the database.
    Returns a session for the connection.

    Args:
        data_dir (string) - Path to configuration database.

    Returns:
        session: Session to the database.
    """
    path = os.path.join(data_dir, "configs.db")
    engine = create_engine('sqlite:///' + path)
    if not os.path.exists(path):
        BASE_TABLE.metadata.create_all(engine)
    session_maker = sessionmaker(bind=engine)
    session = session_maker()
    return session


def clear_config_db(db_session):
    """
    Clears all rows in the CurrentCodeRegion table.
    """
    try:
        db_session.query(CurrentCodeRegion).delete()
    except Exception:
        db_session.rollback()
        raise


def is_current_code_region(db_session, entry):
    """
    Checks if `entry` is already in the CurrentCodeRegions table.
    """
    try:
        found = db_session.query(CurrentCodeRegion).filter(
            CurrentCodeRegion.name == entry.name,
            CurrentCodeRegion.pass_name == entry.pass_name,
            CurrentCodeRegion.func_name == entry.func_name,
            CurrentCodeRegion.code_region_type == entry.code_region_type,
            CurrentCodeRegion.hashcode == entry.hashcode,
            CurrentCodeRegion.debug_file == entry.debug_file,
            CurrentCodeRegion.debug_line == entry.debug_line,
            CurrentCodeRegion.debug_column == entry.debug_column,
            CurrentCodeRegion.invocation == entry.invocation
        ).count()
        return found > 0
    except Exception:
        db_session.rollback()
        raise


def add_current_code_region(db_session, code_region, seen):
    """
    Inserts (code_region, seen) as a row in the CurrentCodeRegions table.
    """
    try:
        entry = CurrentCodeRegion()
        entry.name = code_region["Name"]
        entry.pass_name = code_region["Pass"]
        entry.func_name = code_region["Function"]
        entry.code_region_type = code_region["CodeRegionType"]
        entry.hashcode = code_region["Hashcode"]
        entry.invocation = code_region["Invocation"]
        if "DebugLoc" in code_region:
            entry.debug_file = code_region["DebugLoc"]["File"]
            entry.debug_line = code_region["DebugLoc"]["Line"]
            entry.debug_column = code_region["DebugLoc"]["Column"]
        else:
            entry.debug_file = ""
            entry.debug_line = ""
            entry.debug_column = ""
        entry.seen = seen
        if not is_current_code_region(db_session, entry):
            # Identical opportunities may appear in seperate files when
            # tuning multi-file programs. (ex 521.wrf_r in CPU2017)
            db_session.add(entry)
    except Exception:
        db_session.rollback()
        raise


def is_duplicate_hash(db_session, hashcode, code_region_type, pass_name):
    """
    Determines if the (hash, type, pass) triple is already present
    in the CurrentCodeRegions table.
    """
    try:
        found = db_session.query(CurrentCodeRegion).filter(
            CurrentCodeRegion.hashcode == hashcode,
            CurrentCodeRegion.code_region_type == code_region_type,
            CurrentCodeRegion.pass_name == pass_name
        ).count()
        return found > 1
    except Exception:
        db_session.rollback()
        raise


def optimal_config_exists(db_session, hashcode, code_region_type, pass_name):
    """
    Determines if the (hash, type, pass) triple is already present
    in the OptimalConfig table.
    """
    try:
        result = db_session.query(OptimalConfig).filter(
            OptimalConfig.hashcode == hashcode,
            OptimalConfig.code_region_type == code_region_type,
            OptimalConfig.pass_name == pass_name
        ).one_or_none()
        return result is not None
    except Exception:
        db_session.rollback()
        raise


def get_optimal_config(db_session, hashcode, code_region_type, pass_name):
    """
    Retrieves the optimal configuration stored in the OptimalConfigs
    table for a given (hash, type, pass) triple. Returns None if it does
    not exist.
    """
    try:
        result = db_session.query(OptimalConfig).filter(
            OptimalConfig.hashcode == hashcode,
            OptimalConfig.code_region_type == code_region_type,
            OptimalConfig.pass_name == pass_name
        ).one_or_none()
        return result.params if result is not None else None
    except Exception:
        db_session.rollback()
        raise


def get_current_code_regions(db_session, ignore_seen=False):
    """
    Returns a list of CodeRegionsConfiguration containing all rows
    in currentCodeRegions along with their configuration (if it exists).

    By default, a CodeRegionConfig is only assigned parameters when one
    exists in OptimalConfigs AND the corresponsing code region is marked
    as `seen` in CurrentCodeRegions (When --use-hashed-configs == False, we
    pretend we've never seen any of the code regions before, even if they
    are in the OptimalConfigs table).

    When `ignore_seen` == True, a parameter is assigned whenever one exists
    in OptimalConfigs (Used when generating a baseline config.yaml).
    """
    try:
        results = []
        seen = db_session.query(CurrentCodeRegion).all()
        for row in seen:
            cfg_row = db_session.query(OptimalConfig).filter(
                OptimalConfig.hashcode == row.hashcode,
                OptimalConfig.code_region_type == row.code_region_type,
                OptimalConfig.pass_name == row.pass_name
            ).one_or_none()
            parameters = cfg_row.params if row.seen else None

            if ignore_seen and cfg_row:
                parameters = cfg_row.params

            code_region = CodeRegion(
                name=row.name,
                pass_name=row.pass_name,
                func_name=row.func_name,
                code_region_type=row.code_region_type,
                hashcode=row.hashcode,
                invocation=row.invocation,
            )
            if (row.debug_file != "" and row.debug_line != "" and
                row.debug_column != ""):
                debug_loc = DebugLoc(
                    row.debug_file,
                    int(row.debug_line),
                    int(row.debug_column)
                )
                code_region.debug_loc = debug_loc
            results.append(CodeRegionConfiguration(code_region, parameters))
        return results
    except Exception:
        db_session.rollback()
        raise


def update_optimal_configs(db_session, remarks):
    """
    Insert/update the OptimalConfigs table based on data received in 'remarks'.

    Args:
        db_session - A session to `configs.db`.
        remarks - A list of remarks to consider when updating.
    """
    try:
        for remark in remarks:
            row = db_session.query(OptimalConfig).filter(
                OptimalConfig.hashcode == str(remark.CodeRegionHash),
                OptimalConfig.code_region_type == remark.CodeRegionType,
                OptimalConfig.pass_name == remark.Pass
            ).one_or_none()
            if row:
                # This code region was previously stored in the table.
                db_session.delete(row)
            # Add another row to the OptimalConfig table.
            new_optimal_config = OptimalConfig()
            new_optimal_config.hashcode = str(remark.CodeRegionHash)
            new_optimal_config.code_region_type = remark.CodeRegionType
            new_optimal_config.pass_name = remark.Pass
            new_optimal_config.params = remark.Args
            db_session.add(new_optimal_config)
    except Exception:
        db_session.rollback()
        raise
