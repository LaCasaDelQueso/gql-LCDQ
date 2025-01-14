from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Type

# from pymongo import CursorType


@dataclass
class SQLDomainMapping:
    from_sql: str  # SQL Model key
    to_domain: str  # Domain Model field
    fn: Callable[[Any], Any]  # Mapping Function


def domain_inp_to_out(input_type: Any, output_type: Type[Any]) -> Dict[str, Any]:
    """_summary_

    Parameters
    ----------
    input_type : Any
        _description_
    output_type : Type[Any]
        _description_

    Returns
    -------
    Dict[str, Any]
        _description_
    """
    _model = {}
    _inp_schema = input_type.__dataclass_fields__
    _schema = output_type.__annotations__

    # fill out model mappings
    for inp_k, v in _inp_schema.items():
        if inp_k in _schema:
            _model[inp_k] = input_type.__dict__[inp_k]
    # return model to instantiate
    return _model


def sql_to_domain(
    db_record: Sequence | Dict[str, Any],
    domain_model: Type[Any],
    special_casts: Dict[str, SQLDomainMapping] = {},
) -> Dict[str, Any]:
    """Map SQL Model into Domain Model
        It uses direct mapping for same name keys, but utilizes special casts
        described as following:

        ```
        {
            "sql_key" : SQLDomainMapping
        }
        ```

    Parameters
    ----------
    db_record : Sequence
        _description_
    domain_model : Type[Any]
        _description_
    special_casts : Dict[str, SQLDomainMapping], optional
        _description_, by default {}

    Returns
    -------
    Dict[str, Any]
        Instantiated Domain Model Object
    """
    _model = {}
    _schema = domain_model.__annotations__
    # if db_record is a cursor, convert to dict
    record = dict(db_record) if isinstance(db_record, Sequence) else db_record
    # fill out model mappings
    for sql_k, v in record.items():
        if sql_k in _schema:
            # if key is in special casts run correct implemntation
            if sql_k in special_casts:
                sc = special_casts[sql_k]
                _model[sc.to_domain] = sc.fn(record[sc.from_sql])
            else:
                _model[sql_k] = v
    # return model to instantiate
    return _model


def domain_to_dict(domain_model: object, skip: List[str] = []) -> Dict[str, Any]:
    """Map Domain Model into Dict

    Parameters
    ----------
    domain_model : object
        Domain Model
    skip: List[str]
        List of keys to skip

    Returns
    -------
    Dict[str, Any]
    """
    return {k: v for k, v in domain_model.__dict__.items() if k not in skip}
