package clio.core.db;

import java.sql.Date;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDate;

public class LocalDateAdapter extends JdbcAdapter<LocalDate> {
    public LocalDateAdapter() {
        super(LocalDate.class);
    }

    @Override
    public void insert(LocalDate obj, PreparedStatement stmt) throws SQLException {
        stmt.setDate(1, Date.valueOf(obj));
    }

    @Override
    public LocalDate select(ResultSet result) throws SQLException {
        return result.getDate(1).toLocalDate();
    }
}
