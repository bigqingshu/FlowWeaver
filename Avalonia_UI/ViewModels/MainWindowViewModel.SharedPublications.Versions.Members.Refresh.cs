using System;
using System.Linq;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanLoadMoreSharedPublicationVersionMembers()
    {
        return CanUseEngineActions
            && SelectedSharedPublicationVersion is not null
            && HasMoreSharedPublicationVersionMembers
            && !IsLoadingSharedPublicationVersionMembers;
    }

    [RelayCommand(CanExecute = nameof(CanLoadMoreSharedPublicationVersionMembers))]
    private async Task LoadMoreSharedPublicationVersionMembersAsync()
    {
        if (SelectedSharedPublicationVersion is not null)
        {
            await LoadSelectedSharedPublicationVersionMembersAsync(
                SelectedSharedPublicationVersion,
                reset: false);
        }
    }

    private async Task RefreshSelectedSharedPublicationVersionMembersAsync(
        SharedPublicationListItemViewModel publication)
    {
        await LoadSelectedSharedPublicationVersionMembersAsync(
            publication,
            reset: true);
    }

    private async Task LoadSelectedSharedPublicationVersionMembersAsync(
        SharedPublicationListItemViewModel publication,
        bool reset)
    {
        var requestCancellation = BeginSharedPublicationMembersLoad();
        var cancellationToken = requestCancellation.Token;
        var requestVersion = ++sharedPublicationMembersLoadVersion;
        IsLoadingSharedPublicationVersionMembers = true;
        if (reset)
        {
            sharedPublicationMemberOffset = 0;
            HasMoreSharedPublicationVersionMembers = false;
            SelectedSharedPublicationVersionMembers.Clear();
            SelectedSharedPublicationVersionMember = null;
        }

        try
        {
            var response = await _apiClient.ListSharedPublicationMembersAsync(
                BuildSettings(),
                publication.PublicationId,
                offset: sharedPublicationMemberOffset,
                limit: SharedPublicationMemberPageSize,
                cancellationToken: cancellationToken);
            if (requestVersion != sharedPublicationMembersLoadVersion
                || SelectedSharedPublicationVersion?.PublicationId
                != publication.PublicationId)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                foreach (var member in response.Data.Items)
                {
                    if (SelectedSharedPublicationVersionMembers.All(
                        item => item.TableRefId != member.TableRefId
                            || item.ExportName != member.ExportName))
                    {
                        SelectedSharedPublicationVersionMembers.Add(
                            new SharedPublicationMemberListItemViewModel(
                                member,
                                PreviewSharedPublicationMemberAsync,
                                T));
                    }
                }

                sharedPublicationMemberOffset =
                    response.Data.Offset + response.Data.Items.Length;
                HasMoreSharedPublicationVersionMembers = response.Data.HasMore;
                SelectedSharedPublicationVersionMember ??=
                    SelectedSharedPublicationVersionMembers.FirstOrDefault();
                return;
            }

            SharedPublicationVersionErrorMessage = DescribeError(response);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
        finally
        {
            if (requestVersion == sharedPublicationMembersLoadVersion)
            {
                IsLoadingSharedPublicationVersionMembers = false;
            }

            CompleteSharedPublicationMembersLoad(requestCancellation);
        }
    }

    private System.Threading.CancellationTokenSource BeginSharedPublicationMembersLoad()
    {
        CancelSharedPublicationMembersLoad();
        sharedPublicationMembersLoadCancellation =
            System.Threading.CancellationTokenSource.CreateLinkedTokenSource(
                _shutdown.Token);
        return sharedPublicationMembersLoadCancellation;
    }

    private void CancelSharedPublicationMembersLoad()
    {
        sharedPublicationMembersLoadVersion++;
        sharedPublicationMembersLoadCancellation?.Cancel();
        sharedPublicationMembersLoadCancellation?.Dispose();
        sharedPublicationMembersLoadCancellation = null;
        IsLoadingSharedPublicationVersionMembers = false;
    }

    private void CompleteSharedPublicationMembersLoad(
        System.Threading.CancellationTokenSource request)
    {
        if (ReferenceEquals(sharedPublicationMembersLoadCancellation, request))
        {
            sharedPublicationMembersLoadCancellation = null;
        }

        request.Dispose();
    }

    partial void OnHasMoreSharedPublicationVersionMembersChanged(bool value)
    {
        LoadMoreSharedPublicationVersionMembersCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsLoadingSharedPublicationVersionMembersChanged(bool value)
    {
        LoadMoreSharedPublicationVersionMembersCommand.NotifyCanExecuteChanged();
    }
}
