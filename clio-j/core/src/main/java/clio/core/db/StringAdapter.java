package clio.core.db;

import java.sql.SQLException;

public class StringAdapter extends JdbcAdapter<String> {
    public StringAdapter() {
        super(String.class);
    }

    @Override
    public void insert(String obj, JdbcStatement stmt) throws SQLException {
        stmt.setString(obj);
    }

    @Override
    public String select(JdbcResult result) throws SQLException {
        return result.getString();
    }
}
