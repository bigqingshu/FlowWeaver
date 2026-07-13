using System.Threading;
using System.Threading.Tasks;

namespace Avalonia_UI.Services;

public interface ISqliteDatabaseFileService
{
    Task<SqliteDatabaseFileOpenResult> OpenDatabaseAsync(
        CancellationToken cancellationToken = default);
}

public sealed record SqliteDatabaseFileOpenResult(
    bool Opened,
    bool Cancelled,
    string? Path,
    string? ErrorMessage)
{
    public static SqliteDatabaseFileOpenResult Success(string path)
    {
        return new SqliteDatabaseFileOpenResult(true, false, path, null);
    }

    public static SqliteDatabaseFileOpenResult Cancel()
    {
        return new SqliteDatabaseFileOpenResult(false, true, null, null);
    }

    public static SqliteDatabaseFileOpenResult Failure(string errorMessage)
    {
        return new SqliteDatabaseFileOpenResult(false, false, null, errorMessage);
    }
}
