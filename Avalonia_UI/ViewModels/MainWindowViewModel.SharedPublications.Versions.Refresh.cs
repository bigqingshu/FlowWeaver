using System.Linq;
using System.Threading.Tasks;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanRefreshSharedPublicationVersions()
    {
        return CanUseEngineActions
            && !IsLoadingSharedPublicationVersions
            && (NormalizeFilter(SharedPublicationVersionShareNameFilter) is not null
                || SelectedSharedPublication is not null);
    }

    [RelayCommand(CanExecute = nameof(CanRefreshSharedPublicationVersions))]
    private async Task RefreshSharedPublicationVersionsAsync()
    {
        var shareName = NormalizeFilter(SharedPublicationVersionShareNameFilter)
            ?? SelectedSharedPublication?.ShareName;
        if (string.IsNullOrWhiteSpace(shareName))
        {
            SharedPublicationVersionMessage = T("data.shared_publication_versions_rejected");
            SharedPublicationVersionErrorMessage =
                T("data.share_name_required_for_versions");
            return;
        }

        if (!TryParseLimit(
            SharedPublicationVersionLimitFilter,
            T("data.shared_publication_version_limit_label"),
            out var limit,
            out var error))
        {
            SharedPublicationVersionMessage = T("data.shared_publication_versions_rejected");
            SharedPublicationVersionErrorMessage = error;
            return;
        }

        var requestVersion = ++sharedPublicationVersionsLoadVersion;
        IsLoadingSharedPublicationVersions = true;
        SharedPublicationVersionMessage = F("format.loading_versions_for", shareName);
        SharedPublicationVersionErrorMessage = null;

        try
        {
            var response = await _apiClient.ListSharedPublicationVersionSummariesAsync(
                BuildSettings(),
                shareName,
                offset: 0,
                limit,
                cancellationToken: _shutdown.Token);

            if (requestVersion != sharedPublicationVersionsLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                SharedPublicationVersions.Clear();
                foreach (var publication in response.Data.Items)
                {
                    SharedPublicationVersions.Add(
                        new SharedPublicationListItemViewModel(publication, DisplayTextFormatter));
                }

                SelectedSharedPublicationVersion = SharedPublicationVersions.FirstOrDefault();

                SharedPublicationVersionMessage =
                    F(
                        "format.loaded_shared_publication_versions",
                        SharedPublicationVersions.Count,
                        shareName);
                return;
            }

            SharedPublicationVersionMessage = T("data.shared_publication_versions_refresh_failed");
            SharedPublicationVersionErrorMessage = DescribeError(response);
        }
        finally
        {
            if (requestVersion == sharedPublicationVersionsLoadVersion)
            {
                IsLoadingSharedPublicationVersions = false;
            }
        }
    }

    private async Task RefreshSelectedSharedPublicationVersionMembersAsync(
        SharedPublicationListItemViewModel publication)
    {
        var requestVersion = ++sharedPublicationMembersLoadVersion;
        SelectedSharedPublicationVersionMembers.Clear();
        var response = await _apiClient.ListSharedPublicationMembersAsync(
            BuildSettings(),
            publication.PublicationId,
            offset: 0,
            limit: 100,
            cancellationToken: _shutdown.Token);
        if (requestVersion != sharedPublicationMembersLoadVersion
            || SelectedSharedPublicationVersion?.PublicationId != publication.PublicationId)
        {
            return;
        }

        if (response.Ok && response.Data is not null)
        {
            foreach (var member in response.Data.Items)
            {
                SelectedSharedPublicationVersionMembers.Add(
                    new SharedPublicationMemberListItemViewModel(member));
            }

            return;
        }

        SharedPublicationVersionErrorMessage = DescribeError(response);
    }
}
