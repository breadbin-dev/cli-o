package clio.core.tables;

import clio.core.Dttms;

import java.lang.reflect.Array;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.*;

public class ColumnarTable implements Table {

    private final HashMap<String, ColumnarColumn> header;
    private final Object[] columns;
    private final int rows;

    public ColumnarTable(String[] header, Object[] columns) {
        this.header = new LinkedHashMap<>();
        for (var i = 0; i < header.length; i++)
            this.header.put(header[i], new ColumnarColumn(header[i], i));
        this.columns = columns;
        this.rows = Array.getLength(columns[0]);
    }

    ColumnarTable(HashMap<String, ColumnarColumn> header, Object[] columns) {
        this.header = header;
        this.columns = columns;
        this.rows = Array.getLength(columns[0]);
    }

    @Override
    public int size() {
        return rows;
    }

    @Override
    public Collection<ColumnarColumn> columns() {
        return header.values();
    }

    @Override
    public Column column(String name) {
        return header.get(name);
    }

    @Override
    public Iterable<Row> rows() {
        return () -> new Iterator<>() {
            private int i = 0;

            @Override
            public boolean hasNext() {
                return i < rows;
            }

            @Override
            public Row next() {
                return new ColumnarRow(i++);
            }
        };
    }

    @Override
    public Row row(int index) {
        return new ColumnarRow(index);
    }

    @Override
    public Table slice(List<? extends Row> slice) {
        var rows = (List<ColumnarRow>)slice;
        var columns = new Object[this.columns.length];
        for (var c = 0; c < this.columns.length; c++) {
            switch (this.columns[c]) {
                case int[] ic -> {
                    var nc = (int[]) (columns[c] = new int[rows.size()]);
                    for (var i = 0; i < rows.size(); i++)
                        nc[i] = ic[rows.get(i).index];
                }
                case long[] ic -> {
                    var nc = (long[]) (columns[c] = new long[rows.size()]);
                    for (var i = 0; i < rows.size(); i++)
                        nc[i] = ic[rows.get(i).index];
                }
                case double[] ic -> {
                    var nc = (double[]) (columns[c] = new double[rows.size()]);
                    for (var i = 0; i < rows.size(); i++)
                        nc[i] = ic[rows.get(i).index];
                }
                case char[] ic -> {
                    var nc = (char[]) (columns[c] = new char[rows.size()]);
                    for (var i = 0; i < rows.size(); i++)
                        nc[i] = ic[rows.get(i).index];
                }
                case null, default -> {
                    var ic = (Object[]) this.columns[c];
                    var nc = (Object[]) (columns[c] = new Object[rows.size()]);
                    for (var i = 0; i < rows.size(); i++)
                        nc[i] = ic[rows.get(i).index];
                }
            }
        }

        return new ColumnarTable(header, columns);
    }

    record ColumnarColumn (String name, int index) implements Column { }

    class ColumnarRow implements Row {

        private final int index;

        ColumnarRow(int index) {
            this.index = index;
        }

        private Object column(Column col) {
            return columns[((ColumnarColumn)col).index];
        }

        @Override
        public Object read(Column col) {
            return Array.get(column(col), index);
        }

        @Override
        public String readString(Column col) {
            var c = column(col);
            if (c instanceof char[])
                return Character.toString(((char[])c)[index]);
            else
                return ((String[])c)[index];
        }

        @Override
        public int readInt(Column col) {
            return ((int[])column(col))[index];
        }

        @Override
        public long readLong(Column col) {
            return ((long[])column(col))[index];
        }

        @Override
        public double readDouble(Column col) {
            return ((double[])column(col))[index];
        }

        @Override
        public LocalDateTime readDttm(Column col) {
            var obj = read(col);
            if (obj instanceof LocalDateTime)
                return (LocalDateTime)obj;
            if (obj instanceof Instant)
                return LocalDateTime.ofInstant((Instant)obj, ZoneOffset.UTC);
            if (obj instanceof String)
                return Dttms.parseDttm((String)obj);
            throw new RuntimeException("Unable to read LocalDateTime: " + obj);
        }
    }

    @Override
    public String toString() {
        return toString(10);
    }
}
