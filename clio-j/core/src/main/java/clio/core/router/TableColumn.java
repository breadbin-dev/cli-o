package clio.core.router;

public class TableColumn {

    public static TableColumn of(String field) {
        return new TableColumn(field);
    }

    public static TableColumn of(String field, String headerName) {
        return new TableColumn(field, headerName);
    }

    public String field;
    public String headerName;
    public Boolean rowGroup;
    public String cellClass;
    public Integer width;
    public String type;
    public String valueFormatter;
    public String aggFunc;
    public Boolean hide;

    public TableColumn(String field) {
        this(field, field);
    }

    public TableColumn(String field, String headerName) {
        this.field = field;
        this.headerName = headerName;
    }

    public TableColumn rowGroup() {
        this.rowGroup = true;
        this.hide = true;
        return this;
    }

    public TableColumn cellClass(String cellClass) {
        this.cellClass = cellClass;
        return this;
    }

    public TableColumn aggFunc(String aggFunc) {
        this.aggFunc = aggFunc;
        return this;
    }

    public TableColumn width(int width) {
        this.width = width;
        return this;
    }

    public TableColumn asInt() {
        this.type = "numericColumn";
        this.valueFormatter = "int";
        return this;
    }
}
