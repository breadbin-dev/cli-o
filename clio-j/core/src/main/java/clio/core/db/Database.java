package clio.core.db;

import clio.core.Strings;

import java.sql.Connection;
import java.sql.SQLException;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;

import static clio.core.Strings.f;

public class Database {

    private final Map<Class<?>, JdbcAdapter<?>> adapters = new HashMap<>();

    private final Connection conn;
    private final Syntax syntax;

    public Database(Connection conn, Syntax syntax, JdbcAdapter<?>... adapters) {
        this.conn = conn;
        this.syntax = syntax;

        this.adapters.put(LocalDate.class, new LocalDateAdapter());
        this.adapters.put(String.class, new StringAdapter());

        for (var adapter : adapters)
            this.adapters.put(adapter.adapterCls(), adapter);
    }

    public <T> void write(T obj) {
        var adapter = this.<T>getAdapter(obj.getClass());

        String sql = "insert into " +
                adapter.table() +
                " values (" +
                adapter.placeHolder() +
                ")";

        try (var statement = conn.prepareStatement(sql)){
            adapter.insert(obj, syntax.statement(statement));
            statement.executeUpdate();
        }
        catch (SQLException ex) {
            throw new RuntimeException(ex);
        }
    }

    public <T> void writeAll(Collection<T> objs) {
        for (var obj : objs)
            this.write(obj);
    }

    protected <T> JdbcAdapter<T> getAdapter(Class<?> adapterType) {
        var adapter = this.adapters.get(adapterType);
        if (adapter == null)
            throw new RuntimeException("No adapter registered for " + adapterType);
        return (JdbcAdapter<T>)adapter;
    }

    public <T> List<T> select(String query, Class<T> cls, LocalDateTime fromDttm, LocalDateTime toDttm) {
        return select(query, cls, fromDttm, toDttm, null);
    }

    public <T> List<T> selectAsOf(String query, Class<T> cls, LocalDateTime asOfDttm, String suffix) {
        query += query.contains(" where ") ? " and " : " where ";
        query += "asserted_from <= " + syntax.formatDttm(asOfDttm) + " and (asserted_to is null or asserted_to > " + syntax.formatDttm(asOfDttm) + ")";
        return select(query, cls, null, null, suffix);
    }

    public <T> List<T> select(String query, Class<T> cls, LocalDateTime fromDttm, LocalDateTime toDttm, String suffix) {
        var clause = query.contains(" where ") ? " and " : " where ";

        if (fromDttm != null && toDttm != null)
            query += clause + "dttm between " + syntax.formatDttm(fromDttm.plusNanos(1)) + " and " + syntax.formatDttm(toDttm);
        else if (fromDttm != null)
            query += clause + "dttm > " + syntax.formatDttm(fromDttm);
        else if (toDttm != null)
            query += clause + "dttm <= " + syntax.formatDttm(toDttm);

        if (Strings.hasValue(suffix))
            query += " " + suffix;

        return select(query, cls);
    }

    public <T> List<T> select(String query, Class<T> cls) {
        var adapter = this.<T>getAdapter(cls);

        if (query.contains("{table}"))
            query = query.replace("{table}", adapter.table());

        try (var statement = conn.prepareStatement(query)) {
            try (var results = statement.executeQuery()) {
                var selection = new ArrayList<T>();
                while(results.next())
                    selection.add(adapter.select(syntax.result(results)));

                return selection;
            }
        } catch (SQLException ex) {
            throw new RuntimeException(ex);
        }
    }

    public <T> T selectSingle(String query, Class<T> cls) {
        var result = select(query, cls);
        if (result.isEmpty())
            return null;
        else if (result.size() == 1)
            return result.getFirst();
        else
            throw new RuntimeException(f("Unexpected [{}] results for query: {}", result.size(), query));
    }

    public <T> T ensureSingle(String query, Class<T> cls) {
        var result = selectSingle(query, cls);
        if (result == null)
            throw new RuntimeException("Not found: " + query);
        else
            return result;
    }
}
