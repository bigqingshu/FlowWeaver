using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnSelectedSharedPublicationChanged(
        SharedPublicationCatalogEntryListItemViewModel? value)
    {
        sharedPublicationVersionsLoadVersion++;
        sharedPublicationMembersLoadVersion++;
        IsLoadingSharedPublicationVersions = false;
        SharedPublicationVersions.Clear();
        SelectedSharedPublicationVersion = null;
        SelectedSharedPublicationVersionMembers.Clear();
        SharedPublicationVersionMessage = string.Empty;
        SharedPublicationVersionErrorMessage = null;

        if (value is not null)
        {
            SharedPublicationVersionShareNameFilter = value.ShareName;
        }

        RefreshSharedPublicationVersionsCommand.NotifyCanExecuteChanged();
    }

    partial void OnSelectedSharedPublicationVersionChanged(
        SharedPublicationListItemViewModel? value)
    {
        sharedPublicationMembersLoadVersion++;
        SelectedSharedPublicationVersionMembers.Clear();
        if (value is not null)
        {
            _ = RefreshSelectedSharedPublicationVersionMembersAsync(value);
        }
    }
}
