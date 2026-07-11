using System;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.Services;

public sealed class SharedPublicationCatalogService : ISharedPublicationCatalogService
{
    private readonly IEngineHostApiClient _apiClient;
    private readonly Func<EngineHostConnectionSettings> _settingsProvider;

    public SharedPublicationCatalogService(
        IEngineHostApiClient apiClient,
        Func<EngineHostConnectionSettings> settingsProvider)
    {
        _apiClient = apiClient ?? throw new ArgumentNullException(nameof(apiClient));
        _settingsProvider = settingsProvider
            ?? throw new ArgumentNullException(nameof(settingsProvider));
    }

    public Task<ApiResponseEnvelope<SharedPublicationCatalogPageDto>> SearchSharesAsync(
        string? query,
        int offset,
        int limit,
        CancellationToken cancellationToken = default)
    {
        return _apiClient.ListSharedPublicationCatalogAsync(
            _settingsProvider(),
            query,
            offset,
            limit,
            cancellationToken);
    }

    public Task<ApiResponseEnvelope<SharedPublicationSummaryPageDto>> ListVersionsAsync(
        string shareName,
        int offset,
        int limit,
        CancellationToken cancellationToken = default)
    {
        return _apiClient.ListSharedPublicationVersionSummariesAsync(
            _settingsProvider(),
            shareName,
            offset,
            limit,
            cancellationToken);
    }

    public Task<ApiResponseEnvelope<SharedPublicationMemberPageDto>> ListMembersAsync(
        string publicationId,
        int offset,
        int limit,
        CancellationToken cancellationToken = default)
    {
        return _apiClient.ListSharedPublicationMembersAsync(
            _settingsProvider(),
            publicationId,
            offset,
            limit,
            cancellationToken);
    }
}
