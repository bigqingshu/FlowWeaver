using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private int sharedPublicationsLoadVersion;
    [ObservableProperty]
    private string sharedPublicationShareNameFilter = string.Empty;

    [ObservableProperty]
    private string sharedPublicationLimitFilter = "100";

    [ObservableProperty]
    private bool isLoadingSharedPublications;

    [ObservableProperty]
    private SharedPublicationListItemViewModel? selectedSharedPublication;

    [ObservableProperty]
    private string sharedPublicationMessage = "No shared publications loaded.";

    [ObservableProperty]
    private string? sharedPublicationErrorMessage;

    public ObservableCollection<SharedPublicationListItemViewModel> SharedPublications { get; } =
        new();

    public bool HasSharedPublicationError =>
        !string.IsNullOrWhiteSpace(SharedPublicationErrorMessage);

    public bool IsDataBusy =>
        IsLoadingTableRefs || IsLoadingSharedPublications || IsLoadingSharedPublicationVersions;

    public string ShareText => T("data.share");

    public string ShareNameWatermarkText => T("data.share_name_watermark");

    public string VersionsText => T("data.versions");

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
            var response = await _apiClient.ListSharedPublicationsAsync(
                BuildSettings(),
                NormalizeFilter(SharedPublicationShareNameFilter),
                limit,
                _shutdown.Token);

            if (requestVersion != sharedPublicationsLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                var previousPublicationId = SelectedSharedPublication?.PublicationId;
                SharedPublications.Clear();
                foreach (var publication in response.Data)
                {
                    SharedPublications.Add(
                        new SharedPublicationListItemViewModel(publication, DisplayTextFormatter));
                }

                SelectedSharedPublication = SharedPublications.FirstOrDefault(
                    publication => publication.PublicationId == previousPublicationId)
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

    partial void OnIsLoadingSharedPublicationsChanged(bool value)
    {
        OnPropertyChanged(nameof(IsDataBusy));
        RefreshSharedPublicationsCommand.NotifyCanExecuteChanged();
    }

    partial void OnSharedPublicationErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasSharedPublicationError));
    }
}
