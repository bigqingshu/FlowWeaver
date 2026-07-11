using System.Linq;
using System.Threading.Tasks;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanRefreshSharedPublications()
    {
        return CanUseEngineActions && !IsLoadingSharedPublications;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshSharedPublications))]
    private async Task RefreshSharedPublicationsAsync()
    {
        if (!TryParseLimit(
            SharedPublicationLimitFilter,
            T("data.shared_publication_limit_label"),
            out var limit,
            out var error))
        {
            SharedPublicationMessage = T("data.shared_publication_refresh_rejected");
            SharedPublicationErrorMessage = error;
            return;
        }

        var requestVersion = ++sharedPublicationsLoadVersion;
        IsLoadingSharedPublications = true;
        SharedPublicationMessage = T("data.loading_shared_publications");
        SharedPublicationErrorMessage = null;

        try
        {
            var response = await _apiClient.ListSharedPublicationCatalogAsync(
                BuildSettings(),
                query: NormalizeFilter(SharedPublicationShareNameFilter),
                offset: 0,
                limit,
                cancellationToken: _shutdown.Token);

            if (requestVersion != sharedPublicationsLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                var previousShareName = SelectedSharedPublication?.ShareName;
                SharedPublications.Clear();
                foreach (var entry in response.Data.Items)
                {
                    SharedPublications.Add(
                        new SharedPublicationCatalogEntryListItemViewModel(
                            entry,
                            DisplayTextFormatter));
                }

                SelectedSharedPublication = SharedPublications.FirstOrDefault(
                    publication => publication.ShareName == previousShareName)
                    ?? SharedPublications.FirstOrDefault();
                SharedPublicationMessage =
                    F("format.loaded_shared_publications", SharedPublications.Count);
                return;
            }

            SharedPublicationMessage = T("data.shared_publication_refresh_failed");
            SharedPublicationErrorMessage = DescribeError(response);
        }
        finally
        {
            if (requestVersion == sharedPublicationsLoadVersion)
            {
                IsLoadingSharedPublications = false;
            }
        }
    }
}
