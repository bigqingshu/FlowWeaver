using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnSelectedSharedPublicationChanged(
        SharedPublicationCatalogEntryListItemViewModel? value)
    {
        sharedPublicationVersionsLoadVersion++;
        CancelSharedPublicationMembersLoad();
        ResetSharedPublicationMemberPreviewState();
        IsLoadingSharedPublicationVersions = false;
        SharedPublicationVersions.Clear();
        SelectedSharedPublicationVersion = null;
        SelectedSharedPublicationVersionMembers.Clear();
        SelectedSharedPublicationVersionMember = null;
        HasMoreSharedPublicationVersionMembers = false;
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
        CancelSharedPublicationMembersLoad();
        ResetSharedPublicationMemberPreviewState();
        SelectedSharedPublicationVersionMembers.Clear();
        SelectedSharedPublicationVersionMember = null;
        HasMoreSharedPublicationVersionMembers = false;
        if (value is not null)
        {
            _ = RefreshSelectedSharedPublicationVersionMembersAsync(value);
        }
    }
}
