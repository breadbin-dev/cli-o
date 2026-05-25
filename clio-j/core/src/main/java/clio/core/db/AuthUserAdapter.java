package clio.core.db;

import java.sql.SQLException;

public class AuthUserAdapter extends JdbcAdapter<DBUserAuth.DBUser>  {
    public AuthUserAdapter() {
        super(DBUserAuth.DBUser.class);
    }

    @Override
    public void insert(DBUserAuth.DBUser obj, JdbcStatement stmt) throws SQLException {
        stmt.setString(obj.username());
        stmt.setString(obj.email());
        stmt.setString(obj.passhash());
    }

    @Override
    public DBUserAuth.DBUser select(JdbcResult result) throws SQLException {
        return new DBUserAuth.DBUser(
                result.getString(),
                result.getString(),
                "***"
        );
    }

    @Override
    public String table() {
        return "user";
    }
}
