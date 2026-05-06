package clio.core.tables;

import clio.core.Collections;
import clio.core.XmlReader;
import clio.core.Strings;

import java.util.*;

public class ArrayTable implements Table {

    public static ArrayTable fromHtml(String html) {
        var reader = new XmlReader(html);
        var headers = reader.getOne("thead").getOne("tr").getContent("th");
        var rows = Collections.map(reader.getOne("tbody").get("tr"), tr -> tr.getContent("th", "td"));
        return new ArrayTable(headers, rows);
    }

    public static ArrayTable fromJson(Object obj) {
        var data = (Map<?, ?>)obj;
        var headers = Collections.map((List<Map<String, String>>)data.get("__cols__"), c -> c.get("headerName"));

        var rows = new ArrayList<List<String>>();
        for (var e : data.entrySet()) {
            if (!e.getKey().toString().startsWith("_"))
                rows.add(Collections.map(headers, h -> Strings.nullToEmpty(((Map<String, ?>)e.getValue()).get(h))));
        }
        return new ArrayTable(headers, rows);
    }

    public static ArrayTable fromTsv(Readable tsv) {
        return fromSeperated(tsv, "\t");
    }

    public static ArrayTable fromCsv(Readable csv) {
        return fromSeperated(csv, ",");
    }

    public static ArrayTable fromSeperated(Readable txt, String sep) {
        try (var scanner = new Scanner(txt)) {
            var headers = scanner.nextLine().split(sep);
            var rows = new ArrayList<List<String>>();

            while (scanner.hasNextLine())
                rows.add(Arrays.asList(scanner.nextLine().split(sep)));

            return new ArrayTable(Arrays.asList(headers), rows);
        }
    }

    private final Map<String, Column> columns;
    private final List<? extends List<?>> rows;

    public ArrayTable(Collection<String> headers, List<? extends List<?>> rows) {
        var columns = new LinkedHashMap<String, Column>();
        var loc = 0;
        for (var header : headers)
            columns.put(header, new ArrayColumn(header, loc++));

        this.columns = columns;
        this.rows = rows;
    }

    ArrayTable(Map<String, Column> columns, List<? extends List<?>> rows) {
        this.columns = columns;
        this.rows = rows;
    }

    @Override
    public int size() {
        return rows.size();
    }

    @Override
    public Collection<Column> columns() {
        return columns.values();
    }

    @Override
    public Column column(String name) {
        return Collections.ensure(columns, name);
    }

    @Override
    public Iterable<Row> rows() {
        var i = rows.iterator();
        return () -> new Iterator<>() {
            @Override
            public boolean hasNext() {
                return i.hasNext();
            }

            @Override
            public Row next() {
                return new ArrayRow(i.next());
            }
        };
    }

    @Override
    public Row row(int index) {
        return new ArrayRow(rows.get(index));
    }

    @Override
    public Table slice(List<? extends Row> rows) {
        return new ArrayTable((Map)columns, (List)rows);
    }

    static class ArrayRow implements Row {

        private final List<?> row;

        public ArrayRow(List<?> row) {
            this.row = row;
        }

        @Override
        public String readString(Column col) {
            var result = row.get(((ArrayColumn)col).loc());
            return result.toString();
        }
    }

    record ArrayColumn(String name, int loc) implements Column {}

    @Override
    public String toString() {
        return toString(10);
    }
}
