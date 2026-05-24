import * as agGrid from "ag-grid-enterprise";
import {format} from "../utils";

function intFormat(p) {
    return (p.value)?.toLocaleString(
        undefined,
    )
}

function floatFormat(p) {
    return (p.value)?.toLocaleString(
        undefined,
        {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }
    )
}

function floatFormat5(p) {
    return (p.value)?.toLocaleString(
        undefined,
        {
            minimumFractionDigits: 5,
            maximumFractionDigits: 5
        }
    )
}

function renderHtml(p) {
    return p.value;
}

function mapToRows(rows, existing) {
    let newRows = []
    let updatedRows = []
    for (const [key, row] of Object.entries(rows)) {
        if (!key.startsWith("_")) {
            row["_id"] = key;
            if (existing.has(key)) {
                updatedRows.push(row);
            } else {
                newRows.push(row);
                existing.add(key);
            }
        }
    }
    return [newRows, updatedRows]
}

function stateClass(params) {
    switch(params.value) {
        case "Suspended":
            return "cell-suspended"
        case "Ready":
            return "cell-ready"
        case "Active":
            return "cell-active"
        case "Inactive":
            return "cell-inactive"
        default:
            return ""
    }
}


let statePriority = {
    'Inactive': 0,
    'Ready': 1,
    'Active': 2,
    'Suspended': 3
}


export function aggFuncs() {
    return {
        "countNonZero": (params) => {
            let v = 0;
            for (const i of params.values) {
                if (i !== 0)
                    v += 1
            }
            return v
        },

        "statePriority": (params) => {
            let s = ""
            let v = -1
            for (const i of params.values) {
                let p = statePriority[i]
                if (p > v) {
                    v = p
                    s = i
                }
            }
            return s
        },
    };
}

function leafData(node, data) {
    if (node.leafGroup)
        node.allLeafChildren.forEach(n => leafData(n, data))
    else
        data.push(node.data)
}


function hierarchicalSelection(api, clickedNode) {
    let data = []
    let selection = api.getSelectedNodes()
    if (!selection.includes(clickedNode))
        return [data, []] // clicked somewhere other than selection
    selection.forEach(n => {leafData(n, data)})
    let items = selection.map(x => x.leafGroup ? x.key : x.data._id)
    return [data, items]
}

function contextMenu(params, menu, backgroundFunction) {

    const [rows, items] = hierarchicalSelection(params.api, params.node);

    if (rows.length === 0) {
        // suppress menu unless right click on selected rows
        return ['copy']
    }

    let event = params.event;
    if (event === null || event === undefined) {
        try {
            let node = document.querySelector('.ag-row[row-id="' + params.node.id + '"]');
            let rect = node.getBoundingClientRect();
            event = {clientX: rect.left + window.scrollX, clientY: rect.top + window.scrollY};
        } catch (e) {
            event = {clientX: 0, clientY: 0};
        }
    }
    const actions = []
    const key = items.length === 1 ? items[0] : items.length.toString()
    let couldSeparate = false;

    for (const menuItem of menu) {
        if (menuItem.name === 'separator') {
            if (couldSeparate)
                actions.push('separator')
            couldSeparate = false;
        } else {
            let addItem = true;
            if (menuItem.filter) {
                addItem = false;
                for (const [k, fs] of Object.entries(menuItem.filter)) {
                    let valid = new Set(fs);
                    for (const r of rows) {
                        if (valid.has(r[k])) {
                            addItem = true;
                            break;
                        }
                    }
                    if (addItem)
                        break;
                }
            }
            if (addItem) {
                const vars = { key: key, items: items.join(" ")};
                const cmd = format(menuItem.command, vars);
                actions.push({name: format(menuItem.name, vars), action: () => backgroundFunction(event, cmd)})
                couldSeparate = true;
            }
        }
    }

    if (couldSeparate)
        actions.push('separator')
    actions.push('copy')
    return actions
}


export function dataTable(content, onRefresh, consoleShowing, backgroundFunction) {

    let cols = content["__cols__"];
    let existingRows = new Set();
    let [rows, _norows] = mapToRows(content, existingRows);

    let paging = true;
    let totalRow = false;

    for (const c of cols) {
        const vf = c["valueFormatter"]
        if (vf) {
            if (vf === "int") {
                c["valueFormatter"] = intFormat;
            } else if (vf === "float") {
                c["valueFormatter"] = floatFormat;
            } else if (vf === "float5") {
                c["valueFormatter"] = floatFormat5;
            }
        }
        const cr = c["cellRenderer"]
        if (cr) {
            if (cr === "html") {
                c["cellRenderer"] = renderHtml;
            }
        }
        const cc = c["cellClass"]
        if (cc) {
            if (cc === "stateClass") {
                c["cellClass"] = stateClass;
            }
        }

        if ("rowGroup" in c) {
            paging = false;
        }

        if ("aggFunc" in c) {
            totalRow = true;
        }
    }

    const gridOptions = {
        rowData: rows,
        columnDefs: cols,
        domLayout: 'print',
        autoSizeStrategy: {type: 'fitCellContents'},
        rowSelection: {
            mode: 'multiRow',
            checkboxes: false,
            headerCheckbox: false,
            enableClickSelection: true,
        },
        groupDisplayType: 'multipleColumns',
        suppressAggFuncInHeader: true,
        getRowId: r => r.data["_id"],
        aggFuncs: aggFuncs(),
        onRowGroupOpened: function(params) {
            params.api.autoSizeAllColumns();
        },
        popupParent: document.body,
    };

    if (paging) {
        gridOptions["pagination"] = rows.length > 20
        gridOptions["paginationPageSize"] = 20
    }

    if (totalRow) {
        gridOptions["grandTotalRow"] = "bottom"
    }

    let menu = content["__menu__"];
    if (menu)
        gridOptions["getContextMenuItems"] = p => contextMenu(p, menu, backgroundFunction);

    return {
        shown: consoleShowing,
        gridApi: null,
        existingRows: existingRows,
        init() {
            gridOptions['onGridReady'] = (params) => {
                this.gridApi = params.api;
            };

            onRefresh(
                (result) => {
                    if (result["__update_type__"] === "delta") {
                        const [newRows, updatedRows] = mapToRows(result, this.existingRows);
                        this.gridApi.applyTransaction({
                            update: updatedRows,
                            add: newRows
                        });
                    } else {
                        this.existingRows.clear();
                        const [newRows, updatedRows] = mapToRows(result, this.existingRows);
                        this.gridApi.setGridOption('rowData', newRows)
                    }
                });

            new agGrid.createGrid(this.$refs.tableRef, gridOptions);

            this.$watch('consoleShowing', s => {
                if (s && !this.shown) {
                    this.shown = true;
                    if (this.gridApi) {
                        this.$nextTick(() => {
                            this.gridApi.autoSizeAllColumns();
                        });
                    }
                }
            })
        },
    }
}


export default dataTable;