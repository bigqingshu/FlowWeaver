using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;

namespace Avalonia_UI.Services;

public interface ISqliteTableCatalogService
{
    Task<ApiResponseEnvelope<SqliteTableCatalogDto>> ListTablesAsync(
        string databasePath,
        CancellationToken cancellationToken = default);
}
