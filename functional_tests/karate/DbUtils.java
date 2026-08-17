package karatehelpers;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Small JDBC helper exposed to the Karate features via Java interop
 * (Java.type('karatehelpers.DbUtils')). Karate has no built-in JDBC support, so
 * this is how the functional tests do row-level assertions against the real
 * throwaway Postgres instance.
 *
 * All results are converted to JSON-friendly values so Karate can use its
 * normal `match` syntax against them.
 */
public class DbUtils {

    private static final String URL = "jdbc:postgresql://postgres-test:5432/software_press";
    private static final String USER = "sp_user";
    private static final String PASSWORD = "sp_password";

    private DbUtils() {
    }

    private static Connection getConn() throws SQLException {
        return DriverManager.getConnection(URL, USER, PASSWORD);
    }

    /** Executes a SELECT and returns every row as a map keyed by column label. */
    public static List<Map<String, Object>> query(String sql) {
        List<Map<String, Object>> rows = new ArrayList<>();
        try (Connection conn = getConn();
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(sql)) {
            ResultSetMetaData metaData = rs.getMetaData();
            int columnCount = metaData.getColumnCount();
            while (rs.next()) {
                Map<String, Object> row = new LinkedHashMap<>();
                for (int i = 1; i <= columnCount; i++) {
                    row.put(metaData.getColumnLabel(i), convert(rs.getObject(i)));
                }
                rows.add(row);
            }
        } catch (SQLException e) {
            throw new RuntimeException("DB query failed: " + sql, e);
        }
        return rows;
    }

    /** Executes a SELECT expected to return at most one row, or null if none. */
    public static Map<String, Object> queryRow(String sql) {
        List<Map<String, Object>> rows = query(sql);
        return rows.isEmpty() ? null : rows.get(0);
    }

    /** Executes a SELECT expected to return a single value (e.g. count(*)). */
    public static Object queryValue(String sql) {
        List<Map<String, Object>> rows = query(sql);
        return rows.isEmpty() ? null : rows.get(0).values().iterator().next();
    }

    /** Executes an INSERT/UPDATE/DELETE/DDL and returns the affected row count. */
    public static int execute(String sql) {
        try (Connection conn = getConn();
             Statement stmt = conn.createStatement()) {
            return stmt.executeUpdate(sql);
        } catch (SQLException e) {
            throw new RuntimeException("DB execute failed: " + sql, e);
        }
    }

    private static Object convert(Object value) {
        if (value instanceof UUID) {
            return value.toString();
        }
        if (value instanceof java.sql.Timestamp
                || value instanceof java.sql.Date
                || value instanceof java.sql.Time) {
            return value.toString();
        }
        if (value instanceof byte[]) {
            return Base64.getEncoder().encodeToString((byte[]) value);
        }
        return value;
    }
}
