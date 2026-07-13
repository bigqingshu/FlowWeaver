using System;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.Services;

public sealed class SqliteTableCatalogService : ISqliteTableCatalogService
{
    private readonly IEngineHostApiClient _apiClient;
    private readonly Func<EngineHostConnectionSettings> _settingsProvider;

    public SqliteTableCatalogService(
        IEngineHostApiClient apiClient,
        Func<EngineHostConnectionSettings> settingsProvider)
    {
        _apiClient = apiClient ?? throw new ArgumentNullException(nameof(apiClient));
        _settingsProvider = settingsProvider
            ?? throw new ArgumentNullException(nameof(settingsProvider));
    }

    public Task<ApiResponseEnvelope<SqliteTableCatalogDto>> ListTablesAsync(
        string databasePath,
        CancellationToken cancellationToken = default)
    {
        return _apiClient.ListSqliteTablesAsync(
            _settingsProvider(),
            databasePath,
            cancellationToken);
    }
}
