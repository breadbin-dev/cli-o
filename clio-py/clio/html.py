import re

from IPython.core.display import HTML
from tabulate import tabulate

from clio.arrays import display_dttms
from pandas import MultiIndex

html_empty = HTML("<i>None</i>")


def html_frame(df, raw=False, colalign=None, index=False):
    """specially formatted with reduced set of styles support by email (outlook)"""

    if df is None or df.empty:
        return html_empty

    df = display_dttms(df)

    # Decide how to handle the index
    showindex = False
    df_to_show = df

    if index:
        idx = df.index

        if isinstance(idx, MultiIndex):
            df_to_show = df.reset_index()
            showindex = False
        else:
            # Simple Index: let tabulate show it as index column
            df_to_show = df
            showindex = True

    txt = tabulate(
        df_to_show,
        headers=df_to_show.columns,
        tablefmt="html",
        showindex=showindex,
        intfmt=",",
        missingval="",
        floatfmt=".3f",
        colalign=colalign,
    )

    txt = str(txt)
    txt = txt.replace(
        "<table>",
        '<table border="0" cellspacing="0" cellpadding="0" '
        "style=\"font-family: source-code-pro, Menlo, Monaco, Consolas, 'Courier New', monospace;"
        ' font-size: 11px; padding: 3px 0 0 0;">',
    )

    def td(match):
        style = match.group(1)
        if style is None:
            style = ""
        else:
            style += " "
        element = match.group()[:3]
        border = "#F2F2F2" if "td" in element else "#DDDDDD"
        return (
            f"{element} "
            f'style="{style}padding: 1px 5px; border: 1px solid {border}; '
            f'border-collapse: collapse;">'
        )

    txt = re.sub(r'<th(?:\s+style="([^"]*)")?>', td, txt)
    txt = re.sub(r'<td(?:\s+style="([^"]*)")?>', td, txt)

    row = [0]

    def tr(match):
        x = match.group()[:-1]
        r = row[0]
        row[0] += 1
        if r == 0:
            return x + ' bgcolor="#E6E6FF" style="background-color:#E6E6FF;">'
        elif r % 2 == 0:
            return x + ' bgcolor="#FAFAFA" style="background-color:#FAFAFA;">'
        else:
            return x + ' bgcolor="#FFFFFF" style="background-color:#FFFFFF;">'

    txt = re.sub(r"<tr(?:\s+[^>]*?)?>", tr, txt)

    return txt if raw else HTML(txt)
