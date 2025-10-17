from __future__ import annotations
from typing import List, Tuple
import re
import pandas as pd

_op_pattern = re.compile(r"\s*(==|!=|>=|<=|>|<| in |~)\s*", re.I)

def parse_filters(expr: str) -> List[Tuple[str, str, str]]:
    if not expr:
        return []
    conditions = []
    for raw in expr.split(";"):
        raw = raw.strip()
        if not raw:
            continue
        m = _op_pattern.search(raw)
        if not m:
            raise ValueError(f"Invalid filter segment: {raw}")
        op = m.group(1).strip()
        col = raw[: m.start()].strip()
        val = raw[m.end():].strip()
        conditions.append((col, op, val))
    return conditions

def apply_filters(df: pd.DataFrame, expr: str) -> pd.DataFrame:
    conditions = parse_filters(expr)
    mask = pd.Series([True] * len(df), index=df.index)
    for col, op, val in conditions:
        if col not in df.columns:
            mask &= False
            continue
        series = df[col]
        if op.lower() == "in":
            vals = [v.strip() for v in val.strip("[] ").split(",") if v.strip()]
            parsed = []
            for v in vals:
                try:
                    parsed.append(float(v))
                except ValueError:
                    parsed.append(v)
            mask &= series.isin(parsed)
        elif op == "~":
            sval = val.strip("\"'")
            mask &= series.astype(str).str.contains(sval, case=False, na=False)
        else:
            try:
                rhs = float(val)
                lhs = pd.to_numeric(series, errors="coerce")
            except ValueError:
                rhs = val.strip("\"'")
                lhs = series.astype(str)
            if op == "==":
                mask &= (lhs == rhs)
            elif op == "!=":
                mask &= (lhs != rhs)
            elif op == ">=":
                mask &= (lhs >= rhs)
            elif op == "<=":
                mask &= (lhs <= rhs)
            elif op == ">":
                mask &= (lhs > rhs)
            elif op == "<":
                mask &= (lhs < rhs)
            else:
                raise ValueError(f"Unsupported operator: {op}")
    return df[mask]