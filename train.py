import time

from tqdm import tqdm

from data import DataLoader
from models import create_model
from options.train_options import TrainOptions
from test import run_test, rebuild_shape
from util.writer import Writer

if __name__ == "__main__":
    opt = TrainOptions().parse()
    dataset = DataLoader(opt)
    dataset_size = len(dataset)
    print("#training meshes = %d" % (dataset_size / opt.batch_size))

    model = create_model(opt)
    writer = Writer(opt)
    total_steps = 0

    for epoch in tqdm(range(opt.epoch_count, opt.niter + opt.niter_decay + 1)):
        epoch_start_time = time.time()
        iter_data_time = time.time()
        epoch_iter = 0
        # adjust tqdm for server log and only every 10ths epoch
        for i, data in tqdm(
            enumerate(dataset),
            total=len(dataset) // opt.batch_size,
            miniters=10,
            maxinterval=200,
        ):
            iter_start_time = time.time()
            if i % opt.print_freq == 0:
                t_data = iter_start_time - iter_data_time
            total_steps += opt.batch_size
            epoch_iter += opt.batch_size
            model.set_input(data)
            model.optimize_parameters()

            if i % opt.print_freq == 0:
                loss = model.loss
                t = (time.time() - iter_start_time) / opt.batch_size
                writer.print_current_losses(epoch, epoch_iter, loss, t, t_data)
                writer.plot_loss(loss, epoch, epoch_iter, dataset_size)

            if i % opt.save_latest_freq == 0:
                print(
                    "saving the latest model (epoch %d, total_steps %d)"
                    % (epoch, total_steps)
                )
                model.save_network("latest")

            iter_data_time = time.time()
        if epoch % opt.save_epoch_freq == 0:
            print(
                "saving the model at the end of epoch %d, iters %d"
                % (epoch, total_steps)
            )
            model.save_network("latest")
            model.save_network(epoch)

        print(
            "End of epoch %d / %d \t Time Taken: %d sec"
            % (epoch, opt.niter + opt.niter_decay, time.time() - epoch_start_time)
        )
        model.update_learning_rate()
        if opt.verbose_plot:
            writer.plot_model_wts(model, epoch)

        if epoch % opt.run_test_freq == 0 and epoch > 0:
            mae, sign_accuracy = run_test(epoch)
            writer.plot_acc(mae, epoch, "data/test_mae")
            writer.plot_acc(sign_accuracy, epoch, "data/test_sign_acc")
    print("Finished training")
    # for grid_size in [10, 25, 50, 100, 200]:
    #    rebuild_shape(grid_size)
    writer.close()
