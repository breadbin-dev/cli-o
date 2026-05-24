package clio.core.tables;

import java.util.*;
import clio.core.Collections;

public interface Table {

    int size();

    default boolean isEmpty() {
        return size() == 0;
    }

    Collection<? extends Column> columns();
    Column column(String name);

    Iterable<? extends Row> rows();
    Row row(int index);

    Table slice(List<? extends Row> rows);

    default Map<Object, Table> groupBy(String column) {
        if ("*".equals(column))
            return Map.of("__all__", this);
        else
            return groupBy(column(column));
    }

    default Map<Object, Table> groupBy(Column column) {
        var groups = Collections.collectByKey(rows(), r -> r.read(column));
        return Collections.map(groups, (k, v) -> slice(v));
    }

    default Table aggregateBy(String column, Aggregation... aggregations) {
        var headers = new ArrayList<String>();
        headers.add(column);
        for (var agg : aggregations)
            headers.add(agg.target());
        return aggregateBy(groupBy(column), headers, aggregations);
    }

    default Table aggregateBy(Map<Object, Table> tables, Collection<String> headers, Aggregation... aggregations) {
        var rows = new ArrayList<ArrayList<?>>();
        for (var e : tables.entrySet()) {
            var row = new ArrayList<>();
            row.add(e.getKey());
            for (var agg : aggregations)
                agg.aggregate(e.getValue(), (k, v) -> row.add(v));
            rows.add(row);
        }
        return new ArrayTable(headers, rows);
    }

    default String toString(int maxRows) {
        return toString(this, maxRows);
    }

    static String toString(Table table, int maxRows) {
        var str = new StringBuilder();
        for (var c : table.columns())
            str.append(c.name()).append("\t");
        str.append("\n");

        var i = 0;
        for (var r : table.rows()) {
            for (var c : table.columns())
                str.append(r.read(c)).append("\t");
            str.append("\n");
            if (++i == maxRows)
                break;
        }
        if (i < table.size())
            str.append("... ").append(table.size() - i).append(" rows").append("\n");

        return str.toString();
    }

    default String toHtml() {
        var str = new StringBuilder();
        str.append("<table>");
        str.append("<thead>");
        str.append("<tr>");

        for (var c : columns())
            str.append("<th>").append(c.name()).append("</th>");

        str.append("</tr>");
        str.append("</thead>");
        str.append("<tbody>");

        for (var r : rows()) {
            str.append("<tr>");
            for (var c : columns())
                str.append("<td>").append(r.read(c)).append("</td>");
            str.append("</tr>");
        }
        str.append("</tbody>");
        str.append("</table>");
        return str.toString();
    }
}
