import boto3
from django.core.management.base import BaseCommand
from main.models import Product
from comchecker.settings import AWS_STORAGE_BUCKET_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY


class Command(BaseCommand):
    help = 'Check the image format of product images on AWS S3 and update the Product model'

    def handle(self, *args, **kwargs):
        SIZE = 'medium'
        formats = ['jpg', 'png', 'bmp', 'gif']
        
        # Initialize boto3 client for S3
        s3 = boto3.client('s3',
                          aws_access_key_id=AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                          region_name='eu-north-1')
        bucket_name = AWS_STORAGE_BUCKET_NAME
        products = Product.objects.all()

        for product in products:
            epd_id = product.epd_id
            if not epd_id:
                continue

            found_format = None
            for format in formats:
                prod_key = f'main/images_resized/{epd_id}_prod_1_{SIZE}.{format}'
                # Check if the file exists in the S3 bucket
                try:
                    s3.head_object(Bucket=bucket_name, Key=prod_key)
                    found_format = format
                    break  # Stop once the correct format is found
                except s3.exceptions.ClientError:
                    continue  # Continue to the next format if the file is not found
            
            if found_format:
                # Update the product with the found image format
                product.first_prod_image_format = found_format
                product.save()
                self.stdout.write(self.style.SUCCESS(f'Updated {product.name} with format: {found_format}'))
            
            else:
                self.stdout.write(self.style.WARNING(f'No image found for {product.name}'))

            found_format = None
            for format in formats:
                man_key = f'main/images_resized/{epd_id}_man_1_{SIZE}.{format}'
                # Check if the file exists in the S3 bucket
                try:
                    s3.head_object(Bucket=bucket_name, Key=man_key)
                    found_format = format
                    break  # Stop once the correct format is found
                except s3.exceptions.ClientError:
                    continue  # Continue to the next format if the file is not found
            
            if found_format:
                # Update the product with the found image format
                product.first_man_image_format = found_format
                product.save()
                self.stdout.write(self.style.SUCCESS(f'Updated {product.name} with format: {found_format}'))
            
            else:
                self.stdout.write(self.style.WARNING(f'No image found for {product.name}'))